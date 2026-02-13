# Rig Core: Advanced Usage and Examples

## Tool Integration

### Creating Custom Tools

```rust
use rig::{completion::ToolDefinition, tool::Tool};
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Deserialize)]
struct MathArgs {
    x: i32,
    y: i32,
}

#[derive(Debug, thiserror::Error)]
#[error("Math error")]
struct MathError;

struct Calculator;

impl Tool for Calculator {
    const NAME: &'static str = "add";
    type Error = MathError;
    type Args = MathArgs;
    type Output = i32;

    async fn definition(&self, _prompt: String) -> ToolDefinition {
        ToolDefinition {
            name: "add".to_string(),
            description: "Add two numbers together".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "First number"},
                    "y": {"type": "number", "description": "Second number"}
                }
            }),
        }
    }

    async fn call(&self, args: Self::Args) -> Result<Self::Output, Self::Error> {
        Ok(args.x + args.y)
    }
}
```

### Agent with Tools

```rust
use rig::{completion::Prompt, providers::openai};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    
    let agent = client.agent("gpt-4o")
        .preamble("You are a calculator. Use the provided tools to perform calculations.")
        .tool(Calculator)
        .build();
    
    let response = agent.prompt("What is 15 + 27?").await?;
    println!("{}", response);
    Ok(())
}
```

## Dynamic Tool Selection (RAG Tools)

### Tool with Embedding Support

```rust
use rig::tool::ToolEmbedding;

impl ToolEmbedding for Calculator {
    type InitError = std::convert::Infallible;
    type Context = ();
    type State = ();

    fn init(_state: Self::State, _context: Self::Context) -> Result<Self, Self::InitError> {
        Ok(Calculator)
    }

    fn embedding_docs(&self) -> Vec<String> {
        vec!["Add two numbers together. Useful for arithmetic operations.".to_string()]
    }

    fn context(&self) -> Self::Context {}
}
```

### RAG-Enabled Tool Agent

```rust
use rig::{
    completion::Prompt,
    embeddings::EmbeddingsBuilder,
    providers::openai,
    tool::ToolSet,
    vector_store::{in_memory_store::InMemoryVectorStore, VectorStore},
};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    let embedding_model = client.embedding_model(openai::TEXT_EMBEDDING_ADA_002);
    
    // Create tool set
    let toolset = ToolSet::builder()
        .dynamic_tool(Calculator)
        .build();
    
    // Create embeddings for tools
    let mut vector_store = InMemoryVectorStore::default();
    let embeddings = EmbeddingsBuilder::new(embedding_model.clone())
        .tools(&toolset)?
        .build()
        .await?;
    
    vector_store.add_documents(embeddings).await?;
    let index = vector_store.index(embedding_model);
    
    // Create agent with dynamic tools
    let agent = client.agent("gpt-4o")
        .preamble("You are a helpful assistant with access to various tools.")
        .dynamic_tools(1, index, toolset)
        .build();
    
    let response = agent.prompt("I need to add 25 and 17").await?;
    println!("{}", response);
    Ok(())
}
```

## Multi-Agent Systems

### Creating Multiple Agents

```rust
use rig::{completion::Chat, providers::openai, agent::AgentBuilder};

struct TranslationSystem {
    translator: Agent<openai::CompletionModel>,
    responder: Agent<openai::CompletionModel>,
}

impl TranslationSystem {
    fn new() -> Self {
        let client = openai::Client::from_env();
        
        Self {
            translator: client.agent("gpt-4o")
                .preamble("Translate any input to English. If already English, fix grammar.")
                .build(),
            responder: client.agent("gpt-4o")
                .preamble("You are a helpful assistant.")
                .build(),
        }
    }
}

impl Chat for TranslationSystem {
    async fn chat(&self, prompt: &str, history: Vec<Message>) -> Result<String, PromptError> {
        let translated = self.translator.chat(prompt, history.clone()).await?;
        self.responder.chat(&translated, history).await
    }
}
```

## Data Extraction

### Structured Data Extraction

```rust
use rig::providers::openai;
use serde::{Deserialize, Serialize};
use schemars::JsonSchema;

#[derive(Deserialize, Serialize, JsonSchema)]
struct Person {
    name: Option<String>,
    age: Option<u32>,
    occupation: Option<String>,
    location: Option<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    
    let extractor = client.extractor::<Person>("gpt-4o")
        .preamble("Extract person information from the text.")
        .build();
    
    let text = "John Smith is a 35-year-old software engineer living in San Francisco.";
    let person = extractor.extract(text).await?;
    
    println!("Extracted: {:?}", person);
    Ok(())
}
```

## File Processing

### Loading Documents from Files

```rust
use rig::{
    completion::Prompt,
    loaders::FileLoader,
    providers::openai,
    agent::AgentBuilder,
};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    
    // Load files as context
    let files = FileLoader::with_glob("docs/*.txt")?
        .read_with_path()
        .ignore_errors();
    
    let mut builder = AgentBuilder::new(client.completion_model("gpt-4o"));
    
    for (path, content) in files {
        builder = builder.context(&format!("File {:?}: {}", path, content));
    }
    
    let agent = builder
        .preamble("Answer questions based on the loaded documents.")
        .build();
    
    let response = agent.prompt("Summarize the main topics in the documents").await?;
    println!("{}", response);
    Ok(())
}
```

### PDF Processing (requires "pdf" feature)

```rust
use rig::loaders::PdfFileLoader;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let pdf_loader = PdfFileLoader::with_glob("documents/*.pdf")?;
    
    let pages = pdf_loader
        .load_with_path()
        .by_page()
        .ignore_errors();
    
    for (path, page_contents) in pages {
        for (page_num, content) in page_contents {
            println!("File: {:?}, Page {}: {}", path, page_num, content);
        }
    }
    Ok(())
}
```

## Advanced RAG Patterns

### Multi-Source RAG

```rust
use rig::{
    completion::Prompt,
    embeddings::EmbeddingsBuilder,
    providers::openai,
    vector_store::{in_memory_store::InMemoryVectorStore, VectorStore},
};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    let embedding_model = client.embedding_model(openai::TEXT_EMBEDDING_ADA_002);
    
    // Create multiple knowledge bases
    let mut tech_store = InMemoryVectorStore::default();
    let mut business_store = InMemoryVectorStore::default();
    
    // Add technical documents
    let tech_embeddings = EmbeddingsBuilder::new(embedding_model.clone())
        .simple_document("rust1", "Rust provides memory safety without garbage collection")
        .simple_document("rust2", "Rust has zero-cost abstractions")
        .build().await?;
    
    tech_store.add_documents(tech_embeddings).await?;
    
    // Add business documents  
    let business_embeddings = EmbeddingsBuilder::new(embedding_model.clone())
        .simple_document("market1", "The software market is growing rapidly")
        .simple_document("strategy1", "Focus on developer experience")
        .build().await?;
    
    business_store.add_documents(business_embeddings).await?;
    
    // Create agent with multiple dynamic contexts
    let agent = client.agent("gpt-4o")
        .preamble("You are an expert consultant with access to technical and business knowledge.")
        .dynamic_context(2, tech_store.index(embedding_model.clone()))
        .dynamic_context(1, business_store.index(embedding_model))
        .build();
    
    let response = agent.prompt("How can Rust's features benefit our business strategy?").await?;
    println!("{}", response);
    Ok(())
}
```

## Error Handling Best Practices

### Comprehensive Error Handling

```rust
use rig::{completion::PromptError, providers::openai};

async fn robust_agent_interaction(prompt: &str) -> Result<String, Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    let agent = client.agent("gpt-4o").build();
    
    match agent.prompt(prompt).await {
        Ok(response) => Ok(response),
        Err(PromptError::CompletionError(e)) => {
            eprintln!("Completion failed: {}", e);
            Err(e.into())
        }
        Err(PromptError::ToolError(e)) => {
            eprintln!("Tool execution failed: {}", e);
            Err(e.into())
        }
    }
}
```

## Performance Optimization

### Batch Processing

```rust
use rig::{embeddings::EmbeddingsBuilder, providers::openai};

async fn efficient_embedding_generation() -> Result<(), Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    let embedding_model = client.embedding_model(openai::TEXT_EMBEDDING_ADA_002);
    
    // Process documents in batches
    let documents = vec![
        "Document 1 content",
        "Document 2 content", 
        "Document 3 content",
    ];
    
    let embeddings = EmbeddingsBuilder::new(embedding_model)
        .simple_document("doc1", documents[0])
        .simple_document("doc2", documents[1])
        .simple_document("doc3", documents[2])
        .build()
        .await?;
    
    println!("Generated {} embeddings", embeddings.len());
    Ok(())
}
```

### Caching Strategies

```rust
use std::collections::HashMap;
use rig::completion::Prompt;

struct CachedAgent {
    agent: Agent<openai::CompletionModel>,
    cache: HashMap<String, String>,
}

impl CachedAgent {
    async fn cached_prompt(&mut self, prompt: &str) -> Result<String, PromptError> {
        if let Some(cached) = self.cache.get(prompt) {
            return Ok(cached.clone());
        }
        
        let response = self.agent.prompt(prompt).await?;
        self.cache.insert(prompt.to_string(), response.clone());
        Ok(response)
    }
}
```
