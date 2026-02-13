# Prompt Template Systems (Rig + Rust)

## Template Architecture

Templates help keep prompts consistent and testable. Use them to standardize the structure of preamble/task/schema sections and reduce copy/paste errors.

## Dependencies

- `rig` (rig-core + providers)
- `serde`, `serde_json`
- `thiserror` (for Tool error examples)

### Basic Template Structure
```rust
struct PromptTemplate {
    template: String,
    variables: Vec<String>,
}

impl PromptTemplate {
    fn render(&self, values: &std::collections::HashMap<String, String>) -> Result<String, String> {
        for key in &self.variables {
            if !values.contains_key(key) {
                return Err(format!("Missing required variable: {key}"));
            }
        }

        let mut out = self.template.clone();
        for (k, v) in values {
            out = out.replace(&format!("{{{}}}", k), v);
        }
        Ok(out)
    }
}
```

### Conditional Templates
```rust
fn render_conditional(template: &str, values: &std::collections::HashMap<String, String>) -> String {
    let mut out = template.to_string();
    if values.get("include_examples").map(|v| v == "true").unwrap_or(false) {
        out = out.replace("{{#if include_examples}}", "");
        out = out.replace("{{/if}}", "");
    }
    out
}
```

### Modular Template Composition
```rust
fn compose(components: &[&str]) -> String {
    components.join("\n\n")
}
```

## Common Template Patterns

### Classification Template
```
Classify the following {content_type} into one of: {categories}
Return JSON only: {"label":"..."}

Input: {input}
```

### Extraction Template
```
Extract structured fields: {field_definitions}
Return JSON only.

Input: {input}
```

### Generation Template
```
Generate {output_type} for the following input.
Requirements: {requirements}
Return JSON only: {"output":"..."}

Input: {input}
```

### Transformation Template
```
Transform {source_format} to {target_format}.
Rules: {rules}
Return JSON only: {"output":"..."}

Input: {input}
```

## Advanced Features

### Template Inheritance
```rust
use std::collections::HashMap;

struct TemplateRegistry {
    templates: HashMap<String, HashMap<String, String>>,
}

impl TemplateRegistry {
    fn register(&mut self, name: &str, template: HashMap<String, String>, parent: Option<&str>) {
        let mut merged = template;
        if let Some(p) = parent {
            if let Some(base) = self.templates.get(p) {
                for (k, v) in base {
                    merged.entry(k.clone()).or_insert(v.clone());
                }
            }
        }
        self.templates.insert(name.to_string(), merged);
    }
}
```

### Variable Validation
```rust
fn validate_vars(values: &std::collections::HashMap<String, String>, required: &[&str]) -> Result<(), String> {
    for key in required {
        if !values.contains_key(*key) {
            return Err(format!("Missing variable: {key}"));
        }
    }
    Ok(())
}
```

### Template Caching
```rust
use std::collections::HashMap;

struct CachedTemplate {
    template: String,
    cache: HashMap<String, String>,
}

impl CachedTemplate {
    fn render(&mut self, key: &str, value: &str) -> String {
        if let Some(hit) = self.cache.get(key) {
            return hit.clone();
        }
        let rendered = self.template.replace("{input}", value);
        self.cache.insert(key.to_string(), rendered.clone());
        rendered
    }
}
```

## Multi-Turn Templates

### Conversation Template
```rust
struct Conversation {
    system: String,
    history: Vec<(String, String)>,
}

impl Conversation {
    fn render(&self) -> String {
        let mut out = format!("System: {}\n\n", self.system);
        for (role, content) in &self.history {
            out.push_str(&format!("{}: {}\n\n", role, content));
        }
        out
    }
}
```

### State-Based Templates
```rust
use std::collections::HashMap;

struct StatefulTemplate {
    state: HashMap<String, String>,
    templates: HashMap<String, String>,
}

impl StatefulTemplate {
    fn render(&self, state_name: &str) -> Option<String> {
        self.templates.get(state_name).map(|t| {
            let mut out = t.clone();
            for (k, v) in &self.state {
                out = out.replace(&format!("{{{}}}", k), v);
            }
            out
        })
    }
}
```

## Best Practices

1. Keep templates DRY.
2. Validate variables early.
3. Version template changes like code.
4. Test with diverse inputs.
5. Keep templates small and composable.
6. Use explicit schemas.
7. Provide defaults where sensible.
8. Cache static templates.

## Template Libraries

### Question Answering
```
Answer using only context. If insufficient, say so.
Return JSON only: {"answer":"...","grounded":true|false}

Context: {context}
Question: {question}
```

### Content Generation
```
Write {output_type} with constraints: {constraints}
Return JSON only: {"output":"..."}

Input: {input}
```

## Performance Considerations

- Prebuild static sections.
- Cache rendered templates when inputs repeat.
- Minimize string concatenation in loops.
- Keep logic in code, not template strings.

## Teaching Notes

- A good template is readable by humans and machine-parseable by tooling.
- Use placeholders to force explicitness (`{schema}`, `{constraints}`).
- Keep examples near the schema so the model anchors on output format.

## Extended Template Library (Rig-style)

### RAG with Citations
```
Answer using only provided context.
Cite sources as "file.pdf p1:".
Return JSON only: {"answer":"...","citations":["..."]}

Context: {context}
Question: {question}
```

### Tool-Calling + Schema
```
Call tools only if required data is missing.
Return JSON only: {"status":"approved|pending|rejected","evidence":"file.pdf p1:"}

Input: {input}
```

### Tool-Calling with Validation
```
If required data is missing, call a tool.
If tool fails, return pending with reason.
Return JSON only: {"status":"approved|pending|rejected","evidence":"...","reason":"..."}
```

### Review Template (Diff)
```
Review the diff for correctness, scope, and tests.
Return JSON only: {"issues":[{"severity":"blocking|important|nit","note":"..."}],"verdict":"pass|mixed|fail"}

Diff:
{diff}
```

### Extraction with Validation
```
Extract fields: {fields}
Return JSON only.
If invalid, fix and re-emit JSON only.

Input: {input}
```

### Multi-Section Template (full stack)
```
[Preamble]
{preamble}

[Task]
{task}

[Tools]
{tools}

[Schema]
{schema}

[Verify]
{verify}
```

## Rig Tool Schema Example (Rust)

### Tool definition (Rig Tool trait)
```rust
use rig::{completion::ToolDefinition, tool::Tool};

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
                "properties": {
                    "path": { "type": "string" }
                },
                "required": ["path"]
            })
        }
    }

    async fn call(&self, args: Self::Args) -> Result<Self::Output, Self::Error> {
        Ok(format!("totals from {}", args.path))
    }
}
```

### Tool call prompt hint
```
Call tools only when required input is missing.
Tool: read_sheet(path: string)
```

## Schema Validation Patterns

### Prompt-level validation
```
Return JSON only.
Validate:
- JSON parses
- Required fields present
- Enum values valid
If invalid, fix and re-emit JSON only.
```

### Rust-side validation (serde)
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
