# Rig Agent Patterns (Router -> Specialist -> Verifier)

This guide describes a simple, production-friendly multi-agent workflow using Rig.
The goal is to route tasks to specialists, then verify output before returning.

## Dependencies

- `rig` (rig-core + providers)
- `rig-openai` (if using OpenAI provider)
- `tokio` (async runtime)
- `serde`, `serde_json`, `thiserror`

## 1) Pattern Overview

- **Router**: Classifies the task and selects the specialist.
- **Specialist**: Produces the main output with strict schema.
- **Verifier**: Checks constraints and flags errors or inconsistencies.

Use this when tasks are heterogeneous or high-stakes.

## 2) Roles and Responsibilities

### Router
- Input: user request
- Output: route decision + short rationale
- Constraint: choose one specialist

### Specialist
- Input: original request + context
- Output: JSON-only result
- Constraint: follow schema and tool rules

### Verifier
- Input: specialist output + original request
- Output: pass/fail + corrections or flags

## 3) Routing Template (Prompt)

```
You are a router. Choose exactly one route.
Routes: ["reviewer", "extractor", "summarizer", "qa"]
Return JSON only: {"route":"...","reason":"..."}
```

## 4) Specialist Template (Prompt)

```
You are a {role}.
Use only provided context; call tools if needed.
Return JSON only: {schema}
If invalid, fix and re-emit JSON only.
```

## 5) Verifier Template (Prompt)

```
You are a verifier.
Check:
- JSON schema validity
- Required fields present
- Evidence/citations format
- No hallucinations
Return JSON only: {"verdict":"pass|fail","issues":["..."]}
```

## 6) Rig Orchestration (Rust, compilable)

```rust
use rig::{agent::AgentBuilder, providers::openai};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let openai = openai::Client::from_env();
    let model = openai.completion_model("gpt-4o");

    let router = AgentBuilder::new(model.clone())
        .preamble("You are a router.")
        .build();

    let specialist = AgentBuilder::new(model.clone())
        .preamble("You are a specialist.")
        .build();

    let verifier = AgentBuilder::new(model)
        .preamble("You are a verifier.")
        .build();

    // Router
    let route = router.prompt("route this task").await?;

    // Specialist
    let result = specialist.prompt("do the task").await?;

    // Verifier
    let verdict = verifier.prompt(format!("verify the output: {result}")).await?;

    println!("route={route}");
    println!("result={result}");
    println!("verdict={verdict}");

    Ok(())
}
```

## 6b) Tool-enabled Specialist (Rig Tool trait, compilable)

```rust
use rig::{agent::AgentBuilder, completion::ToolDefinition, providers::openai, tool::Tool};

#[derive(serde::Deserialize)]
struct ReadSheetArgs {
    path: String,
}

#[derive(Debug, thiserror::Error)]
#[error("IO error")]
struct ReadSheetError;

#[derive(serde::Deserialize, serde::Serialize)]
struct ReadSheet;

impl Tool for ReadSheet {
    const NAME: &'static str = "read_sheet";
    type Error = ReadSheetError;
    type Args = ReadSheetArgs;
    type Output = String;

    async fn definition(&self, _prompt: String) -> ToolDefinition {
        ToolDefinition {
            name: "read_sheet".to_string(),
            description: "Read a spreadsheet and return totals".to_string(),
            parameters: serde_json::json!({
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            })
        }
    }

    async fn call(&self, args: Self::Args) -> Result<Self::Output, Self::Error> {
        Ok(format!("totals from {}", args.path))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let openai = openai::Client::from_env();
    let model = openai.completion_model("gpt-4o");

    let tool_specialist = AgentBuilder::new(model)
        .preamble("You are a specialist who can call tools.")
        .tool(ReadSheet)
        .build();

    let result = tool_specialist
        .prompt("compute totals from costs.xlsx")
        .await?;

    println!("{result}");
    Ok(())
}
```

## 6c) Verifier with serde schema validation (compilable)

```rust
use serde::Deserialize;

#[derive(Deserialize)]
struct OutputSchema {
    status: String,
    evidence: String,
}

fn verify_output(json_text: &str) -> Result<OutputSchema, String> {
    serde_json::from_str(json_text).map_err(|e| e.to_string())
}

fn main() {
    let output_json = r#"{"status":"approved","evidence":"file.pdf p1:"}"#;
    let parsed = verify_output(output_json).expect("valid schema");
    println!("{}", parsed.status);
}
```

## 7) Handoff Rules

- Router must output exactly one route.
- Specialist must not alter the schema shape.
- Verifier should not rewrite content unless failing.

## 8) Failure Handling

- If router fails -> fallback to generalist.
- If verifier fails -> ask specialist to fix and retry once.
- If still failing -> return error state with reasons.

## 9) Suggested Schemas

### Router Output
```json
{"route":"reviewer","reason":"requires policy checks"}
```

### Verifier Output
```json
{"verdict":"fail","issues":["missing evidence", "invalid enum"]}
```

## 10) Notes

- Keep each agent prompt short and consistent.
- Avoid tool calls in verifier unless strictly required.
- Log routing and verification results for debugging.
