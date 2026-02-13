---
name: rig-core
description: Rig (rig.rs) helper for Rust agents - use for setup, completions, embeddings, tools/function-calling, RAG, providers, and doc lookups when building or debugging Rig agents.
---

Use this skill when building or troubleshooting Rig-based agents.

## Quick start (Rust)
- Add deps: `cargo add rig-core` (plus provider crate if needed, e.g., `rig-openai`).
- Env: set provider API key (e.g., `OPENAI_API_KEY`) and proxy if required.
- Minimal agent:
```rust
use rig_core::{prelude::*, AgentBuilder};

let agent = AgentBuilder::default()
    .model("gpt-4o-mini")?
    .preamble("You are a fact-checked reviewer.")
    .build()?;

let reply = agent.prompt("Summarize the doc.")?.await?;
println!("{}", reply.message().content_text());
```

## Tools / function calling
1) Implement a `Tool` with `name`, `description`, `parameters` schema, and `run`.  
2) Register with `.tool(my_tool)` on the builder.  
3) In preamble, state when to call tools vs answer directly.  
See `references/rig_quickstart.md` for a full snippet.

## Embeddings
- Use `EmbeddingsBuilder` with `.document(text)` then `.build().await?`.  
- Choose provider model; store vectors in your DB; see `references/rig_quickstart.md`.

## RAG pattern
1) Retrieve context (top-k).  
2) Build prompt with citations.  
3) Keep total tokens in budget; include “if insufficient context, say so.”  
Reference: `references/rig_advanced_usage.md`.

## Best practices
- Keep preamble short (<120 tokens); move stable rules there.  
- Add output contracts (JSON) and a self-check step.  
- Log provider requests/responses for debugging; trim prompts for cost.  
- For tool-heavy flows, prefer deterministic parameter schemas and explicit call criteria.

## Where to look
- `references/rig_outline.md` - map of docs links.  
- `references/rig_quickstart.md` - install + completion/embedding/tool snippets.  
- `references/rig_api_reference.md` - key builder and agent methods.  
- `references/rig_best_practices.md` - model choice, retries, cost/perf.  
- `references/rig_advanced_usage.md` - custom tools, RAG, advanced patterns.  

Keep context lean: load only the reference you need. For anything missing, open the specific docs.rig.rs page and summarize.

