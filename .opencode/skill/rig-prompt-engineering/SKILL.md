---
name: rig-prompt-engineering
description: Practical prompt patterns for Rig-based Rust agents. Use for system/preamble design, tool calling, schema validation, few-shot examples, verification steps, and multi-agent orchestration.
---

Use this when designing or debugging prompts for Rig agents, especially tool-using or JSON-producing Rust agents.

## 0) Required inputs (ask if missing)

- Target model and provider (Rig config)
- Task intent and success criteria
- Required tools and call criteria
- Output schema (JSON shape + constraints)
- Validation expectations (prompt-level + Rust-side)

## 1) Rig prompt stack (progressive)

- **Preamble**: role + boundaries + success criteria; keep short (<120 tokens).
- **Task**: explicit inputs, defaults, and constraints.
- **Tools**: when to call vs answer directly; include stop conditions.
- **Output contract**: JSON shape, allowed values, length limits.
- **Verification**: self-check list; re-emit JSON only if invalid.

## 2) Core patterns (Rust/Rig)

### Minimal agent (Rust)
```rust
use rig::{agent::AgentBuilder, providers::openai};

let openai = openai::Client::from_env();
let gpt4o = openai.completion_model("gpt-4o");

let agent = AgentBuilder::new(gpt4o)
    .preamble("You are a concise, evidence-grounded reviewer.")
    .build();

let reply = agent.prompt("Summarize the doc.").await?;
println!("{}", reply);
```

### Tool call criteria (prompt)
```rust
let preamble = r#"Call tools only when required input is missing or computation is external.
If no tool is needed, answer directly."#;
```

### Schema guard (prompt)
```rust
let preamble = r#"Return JSON only: {\"status\":\"approved|pending|rejected\",\"evidence\":\"<50 chars, include filename p<page>:\"}
If invalid, fix and re-emit JSON only."#;
```

### Rig tool definition (Rust)
```rust
use rig::{completion::ToolDefinition, tool::Tool};

#[derive(serde::Deserialize)]
struct AddArgs { x: i32, y: i32 }

#[derive(Debug, thiserror::Error)]
#[error("Math error")]
struct MathError;

#[derive(serde::Deserialize, serde::Serialize)]
struct Adder;

impl Tool for Adder {
    const NAME: &'static str = "add";
    type Error = MathError;
    type Args = AddArgs;
    type Output = i32;

    async fn definition(&self, _prompt: String) -> ToolDefinition {
        ToolDefinition {
            name: "add".to_string(),
            description: "Add x and y together".to_string(),
            parameters: serde_json::json!({
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"}
                },
                "required": ["x", "y"]
            })
        }
    }

    async fn call(&self, args: Self::Args) -> Result<Self::Output, Self::Error> {
        Ok(args.x + args.y)
    }
}
```

### Rust-side schema validation (serde)
```rust
use serde::Deserialize;

#[derive(Deserialize)]
struct OutputSchema {
    status: String,
    evidence: String,
}

fn validate(json_text: &str) -> Result<OutputSchema, String> {
    serde_json::from_str(json_text).map_err(|e| e.to_string())
}
```

### JSON Schema validation (Rust)
```rust
// Example using jsonschema crate (pseudo-usage)
// let schema = serde_json::from_str(SCHEMA_JSON)?;
// let compiled = jsonschema::JSONSchema::compile(&schema)?;
// let instance = serde_json::from_str(json_text)?;
// compiled.validate(&instance).map_err(|e| e.to_string())?;
```

## 3) Core prompt patterns (short)

- **Hidden reasoning**: Think step by step, then answer concisely.
- **Decomposition**: plan -> act -> reflect (best for multi-tool flows).
- **Retrieval grounding**: Use only provided context; if insufficient, say what is missing.
- **Schema guard**: JSON-only, validate, fix, re-emit JSON only.
- **Refusal**: If out of scope, respond with {"status":"refused","reason":"..."}.
- **Style tags**: compact labels like [status=approved|pending|rejected].

## 4) Few-shot guidance

- 1-3 short examples is typical.
- Mirror the exact JSON schema.
- Include one tool-using example and one non-tool example.
- Add one refusal/insufficient example for safety.

## 5) Iteration loop

1. Draft minimal prompt (preamble + task + schema).
2. Test 5-10 edge cases; log failures.
3. Trim tokens; move stable rules to preamble.
4. Add 1-2 canonical examples; keep them short.
5. Re-test and version prompts like code.

## 6) Debug checklist

- **Schema errors**: tighten allowed values/lengths; remind to re-emit JSON only.
- **Hallucinations**: cite only provided context; if none, say insufficient context.
- **Tool misuse**: clarify call criteria and add counter-example.
- **Verbosity**: enforce short answers and trim examples.

## 7) References (load as needed)

- `references/prompt-optimization.md` - Baseline/iteration/A-B testing, failure analysis, metrics, versioning, and statistical significance sketches.
- `references/prompt-templates.md` - Template systems, inheritance, validation patterns, schema enforcement, and extended Rig-style libraries.
- `references/chain-of-thought.md` - CoT patterns, ToT branching + scoring, verification flows, and evaluation notes.
- `references/few-shot-learning.md` - Example selection strategies, token-aware truncation, failure-mode guidance, and prompt templates.
- `references/system-prompts.md` - System prompt structure, role patterns, testing matrix, and strict schema constraints.
- `references/agent-patterns.md` - Router/specialist/verifier orchestration, handoff rules, and prompt templates.
- Assets: `assets/prompt-template-library.md` (template catalog) and `assets/few-shot-examples.json` (schema-aligned examples).
