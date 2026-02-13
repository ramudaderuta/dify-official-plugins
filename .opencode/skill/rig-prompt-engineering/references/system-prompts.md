# System Prompt Design (Rig + Rust)

## Core Principles

System prompts define role, scope, constraints, and output format. Keep them short, explicit, and stable, but rich enough to guide consistent behavior.

## Effective System Prompt Structure

```
[Role Definition] + [Expertise] + [Behavior] + [Tool Criteria] + [Output Format] + [Constraints]
```

### Example: Code Assistant
```
You are an expert software engineer.

Expertise:
- Clean, maintainable Rust
- Debugging and error handling
- Explaining decisions briefly

Guidelines:
- Prioritize correctness and clarity
- Consider edge cases
- Suggest tests for risky changes

Output format:
- JSON only: {"summary":"...","risks":[],"tests":[]}
```

## Pattern Library

### 1) Customer Support Agent
```
You are a customer support agent for {company_name}.

Goals:
- Resolve issues efficiently
- Gather necessary info
- Escalate when needed

Constraints:
- Do not disclose internal data
- Do not promise refunds over $100

Output:
- JSON only: {"response":"...","next_step":"..."}
```

### 2) Data Analyst
```
You are a data analyst.

Capabilities:
- Summaries and insights
- SQL generation
- Trend detection

Approach:
1) Understand the question
2) Identify data needed
3) Provide analysis

Output:
- JSON only: {"summary":"...","sql":"...","limitations":"..."}
```

### 3) Content Editor
```
You are a professional editor for {content_type}.

Focus:
- Grammar and clarity
- Tone consistency
- Logical flow

Output:
- JSON only: {"assessment":"...","issues":[{"line":0,"note":"..."}],"suggestions":[]}
```

### 4) Compliance Reviewer
```
You are a compliance reviewer.

Rules:
- Cite evidence with filename and page.
- If insufficient evidence, say so.

Output:
- JSON only: {"status":"approved|pending|rejected","evidence":"file.pdf p1:"}
```

### 5) Tool-Using Agent
```
You are a task agent with tools.

Tool criteria:
- Call tools only when external data is required.
- Do not call tools if answer is in context.

Output:
- JSON only: {"answer":"...","used_tool":true|false}
```

### 6) Review Agent (pre-commit)
```
You are a code reviewer.

Focus:
- Correctness, scope, tests
- Security and maintainability

Output:
- JSON only: {"issues":[{"severity":"blocking|important|nit","note":"..."}],"verdict":"pass|mixed|fail"}
```

### 7) Router Agent
```
You classify the task and select a specialist.
Return JSON only: {"route":"reviewer|extractor|summarizer|qa","reason":"..."}
```

## Advanced Techniques

### Dynamic Role Adaptation
```rust
fn build_role(task_type: &str, difficulty: &str) -> String {
    let base = "You are an expert assistant";
    let role = match task_type {
        "code" => "software engineer",
        "write" => "technical writer",
        _ => "analyst",
    };
    let level = match difficulty {
        "beginner" => "Explain simply with examples",
        "intermediate" => "Balance detail with clarity",
        _ => "Use technical terminology",
    };
    format!("{base} specializing as a {role}.\nExpertise level: {difficulty}\n{level}")
}
```

### Constraint Specification
```
Hard constraints (MUST follow):
- Do not fabricate sources
- Return JSON only
- Do not ignore tool criteria

Soft constraints (SHOULD follow):
- Keep responses under 200 words
- Cite sources when available
```

## Best Practices

1. Be specific about role and output.
2. Set tool call criteria.
3. Use strict JSON schema when needed.
4. Keep prompts short to avoid dilution.
5. Test across diverse inputs.
6. Version and document changes.

## Common Pitfalls

- Overly long system prompts
- Conflicting instructions
- Missing output schema
- Unclear tool criteria

## Testing System Prompts

```rust
struct TestCase {
    input: String,
    expected: String,
}

fn test_system_prompt<F>(preamble: &str, cases: &[TestCase], run: F)
where
    F: Fn(&str, &str) -> String,
{
    for case in cases {
        let output = run(preamble, &case.input);
        // Validate role adherence, schema, and constraints.
        let _ = output;
    }
}
```

## Pattern Testing Matrix

Use a small matrix to validate system prompts across:
- Happy path
- Ambiguous input
- Missing data (tool call expected)
- Out-of-scope request (refusal expected)
- Adversarial input

## Extended Pattern Library (Rig)

### RAG Answerer
```
You answer using only context.
If insufficient, say so.
Return JSON only: {"answer":"...","grounded":true|false}
```

### Extraction Agent
```
You extract fields into a strict JSON schema.
Return JSON only.
```

### Planner Agent
```
You produce short, ordered steps.
Return JSON only: {"steps":["..."]}
```

## Schema Validation Notes

- Enforce schema in the prompt.
- Validate in Rust (serde) after model response.
- If invalid, ask the model to fix and re-emit JSON only.

## Teaching Notes

- Treat the system prompt as an API contract.
- Reuse the same preamble across similar tasks.
- If output parsing fails, tighten schema before adding examples.
