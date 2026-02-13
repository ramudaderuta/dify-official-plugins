# Rig Quickstart (from https://docs.rig.rs/docs/quickstart)

## Install
- Add crates: `cargo add rig-core tokio`
- Set provider credentials (e.g., `OPENAI_API_KEY`) in the environment before running.

## Basic completion
```rust
use rig::completion::Prompt;
use rig::providers::openai;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Creates OpenAI client from env (`OPENAI_API_KEY`)
    let client = openai::Client::from_env();

    // Build an agent for a model and send a prompt
    let gpt4 = client.agent("gpt-4").build();
    let response = gpt4.prompt("Who are you?").await?;

    println!("GPT-4: {response}");
    Ok(())
}
```

## Embeddings
```rust
use rig::{embeddings::EmbeddingsBuilder, providers::openai};

let client = openai::Client::from_env();
let model = client.embedding_model("text-embedding-ada-002");

let embeddings = EmbeddingsBuilder::new(model)
    .document("Some text")?
    .document("More text")?
    .build()
    .await?;
```

## Tools (function calling) example
```rust
use rig::{
    providers, tool::{Tool, ToolDefinition}
};
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
struct AddArgs { x: i32, y: i32 }

#[derive(Deserialize, Serialize)]
struct Adder;

#[derive(thiserror::Error, Debug)]
enum MathError { #[error("bad math")] Bad }

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
                    "x": { "type": "number", "description": "First number" },
                    "y": { "type": "number", "description": "Second number" }
                }
            }),
        }
    }

    async fn call(&self, args: Self::Args) -> Result<Self::Output, Self::Error> {
        Ok(args.x + args.y)
    }
}

// Build agent with a tool and prompt it
let agent = providers::openai::Client::from_env()
    .agent(providers::openai::GPT_4O)
    .preamble("You are a calculator…")
    .max_tokens(1024)
    .tool(Adder)
    .build();
```

## Run
- Use `cargo run` (after adding deps) to execute the examples.
