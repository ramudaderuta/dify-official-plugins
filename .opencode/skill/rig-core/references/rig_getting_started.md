# Rig Core: Getting Started Guide

## Overview

Rig-core is a Rust library for building LLM-powered applications with focus on ergonomics and modularity. It provides unified interfaces for multiple LLM providers and vector stores.

## Quick Start

### Installation

Add to your `Cargo.toml`:

```toml
[dependencies]
rig-core = "0.2.7"
tokio = { version = "1.0", features = ["full"] }
```

### Basic Agent

```rust
use rig::{completion::Prompt, providers::openai};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    let agent = client.agent("gpt-4o")
        .preamble("You are a helpful assistant.")
        .build();
    
    let response = agent.prompt("Hello!").await?;
    println!("{}", response);
    Ok(())
}
```

### Agent with Context

```rust
use rig::{completion::Prompt, providers::openai};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = openai::Client::from_env();
    let agent = client.agent("gpt-4o")
        .preamble("You are a technical assistant.")
        .context("Rust is a systems programming language focused on safety and performance.")
        .build();
    
    let response = agent.prompt("What is Rust?").await?;
    println!("{}", response);
    Ok(())
}
```

### RAG System

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
    
    // Create vector store
    let mut vector_store = InMemoryVectorStore::default();
    let embeddings = EmbeddingsBuilder::new(embedding_model.clone())
        .simple_document("doc1", "Rust is memory safe without garbage collection.")
        .simple_document("doc2", "Rust has zero-cost abstractions.")
        .build()
        .await?;
    
    vector_store.add_documents(embeddings).await?;
    let index = vector_store.index(embedding_model);
    
    // Create RAG agent
    let agent = client.agent("gpt-4o")
        .preamble("Answer questions using the provided context.")
        .dynamic_context(1, index)
        .build();
    
    let response = agent.prompt("What makes Rust special?").await?;
    println!("{}", response);
    Ok(())
}
```

## Core Concepts

### Agent
- Central component combining model, prompt, context, and tools
- Built using `AgentBuilder` pattern
- Supports static and dynamic content

### Models
- **Completion Models**: Generate text responses
- **Embedding Models**: Create vector representations

### Vector Stores
- Store and query document embeddings
- Enable RAG functionality
- Support similarity search

### Tools
- Extend agent capabilities
- Define custom functions
- Support async operations

## Environment Setup

Set required API keys:

```bash
export OPENAI_API_KEY="your-key-here"
export COHERE_API_KEY="your-key-here"  # if using Cohere
```

## Supported Providers

- **OpenAI**: GPT models, embeddings
- **Cohere**: Command models, embeddings  
- **Anthropic**: Claude models
- **Google**: Gemini models
- **Perplexity**: Various models

## Next Steps

1. Try the basic examples above
2. Explore tool integration
3. Build custom RAG systems
4. Integrate with vector databases
