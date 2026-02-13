# Rig Framework: Best Practices Guide

## Agent Configuration Best Practices

### Environment Setup
- Always use environment variables for API keys, never hardcode them
- Use `Client::from_env()` for simplified client initialization
- Set up proper error handling for missing environment variables

```rust
// Good
let client = openai::Client::from_env();

// Avoid
let client = openai::Client::new("hardcoded-key");
```

### Model Selection
- Choose smaller models (GPT-3.5, Command-R) for simple tasks to reduce cost and latency
- Use larger models (GPT-4, Claude) for complex reasoning tasks
- Consider model-specific strengths (Claude for long context, Cohere for search)

### Agent Building
- Use descriptive preambles to clearly define agent behavior
- Limit context documents to avoid token overflow
- Structure context content as clear paragraphs or definitions
- Set appropriate temperature values (0.0 for deterministic, higher for creative tasks)

```rust
let agent = client.agent("gpt-4o")
    .preamble("You are a technical assistant specializing in Rust programming.")
    .context("Rust is a systems programming language focused on safety and performance.")
    .temperature(0.1) // Low for technical accuracy
    .max_tokens(1000)
    .build();
```

## Tool Integration Best Practices

### Tool Design
- Provide detailed descriptions and parameter schemas for tools
- Keep tool logic simple and focused on single responsibilities
- Implement proper error handling in tool implementations
- Use descriptive parameter names and descriptions

```rust
impl Tool for Calculator {
    async fn definition(&self, _prompt: String) -> ToolDefinition {
        ToolDefinition {
            name: "add".to_string(),
            description: "Add two numbers together. Use for arithmetic operations.".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "x": {
                        "type": "number",
                        "description": "The first number to add"
                    },
                    "y": {
                        "type": "number", 
                        "description": "The second number to add"
                    }
                }
            }),
        }
    }
}
```

### Dynamic Tool Selection
- Use dynamic tools for large tool sets to avoid prompt overflow
- Limit the number of tools retrieved (typically 1-4)
- Regularly update tool embeddings to maintain relevance
- Provide clear tool descriptions for better embedding quality

## RAG Implementation Best Practices

### Vector Store Management
- Choose appropriate vector store backends for your scale:
  - InMemoryVectorStore: Development and small datasets
  - External databases (LanceDB, Qdrant): Production and large datasets
- Pre-compute embeddings when possible to reduce API calls
- Use batch processing for embedding generation

### Context Retrieval
- Limit dynamic context retrieval (typically 1-3 documents)
- Use appropriate embedding models for your domain
- Consider separate models for document and query embeddings (Cohere)
- Verify retrieved context relevance before including

```rust
let rag_agent = client.agent("gpt-4o")
    .preamble("Answer using the provided context documents.")
    .dynamic_context(2, index) // Limit to 2 most relevant docs
    .build();
```

## Performance Optimization

### API Efficiency
- Implement request caching for repeated queries
- Use batch operations when available
- Set reasonable timeout values for HTTP requests
- Implement retry mechanisms with exponential backoff

### Memory Management
- Stream process large files instead of loading entirely into memory
- Implement pagination for large document sets
- Clear unused embeddings and caches periodically
- Monitor memory usage in production

### Concurrent Processing
- Use async/await for non-blocking operations
- Process independent tasks in parallel
- Batch similar operations together
- Avoid blocking the async runtime

```rust
// Good: Parallel processing
let futures: Vec<_> = documents.iter()
    .map(|doc| embedding_model.embed_document(doc))
    .collect();
let embeddings = futures::future::try_join_all(futures).await?;

// Avoid: Sequential processing
let mut embeddings = Vec::new();
for doc in documents {
    embeddings.push(embedding_model.embed_document(doc).await?);
}
```

## Error Handling Best Practices

### Comprehensive Error Management
- Handle all error types appropriately (API, network, parsing)
- Provide meaningful error messages to users
- Implement graceful degradation when possible
- Log errors with sufficient context for debugging

```rust
match agent.prompt("question").await {
    Ok(response) => println!("{}", response),
    Err(PromptError::CompletionError(e)) => {
        eprintln!("Model completion failed: {}", e);
        // Implement fallback or retry logic
    }
    Err(PromptError::ToolError(e)) => {
        eprintln!("Tool execution failed: {}", e);
        // Handle tool-specific errors
    }
}
```

### Resilience Patterns
- Implement circuit breakers for external API calls
- Use fallback responses when primary systems fail
- Validate inputs before processing
- Set appropriate timeouts for all operations

## Multi-Agent System Best Practices

### Agent Coordination
- Design agents with single, clear responsibilities
- Use well-defined interfaces between agents
- Maintain conversation history appropriately
- Implement proper state management

### Communication Patterns
- Pass context explicitly between agents
- Log intermediate results for debugging
- Handle agent failures gracefully
- Avoid circular dependencies between agents

```rust
struct TranslationSystem {
    translator: Agent<M>,
    responder: Agent<M>,
}

impl Chat for TranslationSystem {
    async fn chat(&self, prompt: &str, history: Vec<Message>) -> Result<String, PromptError> {
        // Step 1: Translate input
        let translated = self.translator.chat(prompt, history.clone()).await?;
        println!("Translated: {}", translated); // Log for debugging
        
        // Step 2: Generate response
        self.responder.chat(&translated, history).await
    }
}
```

## Security Best Practices

### API Key Management
- Store API keys in environment variables or secure vaults
- Rotate API keys regularly
- Use different keys for different environments
- Monitor API key usage and set up alerts

### Input Validation
- Sanitize user inputs before processing
- Validate file paths and prevent directory traversal
- Limit input sizes to prevent resource exhaustion
- Implement rate limiting for user requests

### Data Privacy
- Avoid logging sensitive information
- Implement data retention policies
- Use encryption for data at rest and in transit
- Follow privacy regulations (GDPR, CCPA)

## Testing Best Practices

### Unit Testing
- Mock external API calls in tests
- Test error conditions and edge cases
- Validate tool parameter schemas
- Test embedding generation and retrieval

### Integration Testing
- Test complete workflows end-to-end
- Validate API integrations with real services
- Test performance under load
- Verify error handling in realistic scenarios

### Monitoring and Observability
- Implement comprehensive logging with structured data
- Monitor API usage and costs
- Track response times and error rates
- Set up alerts for system health

```rust
// Enable detailed logging
tracing_subscriber::fmt()
    .with_max_level(tracing::Level::DEBUG)
    .with_target(false)
    .init();
```

## Production Deployment

### Scalability Considerations
- Use connection pooling for HTTP clients
- Implement horizontal scaling for stateless components
- Cache frequently accessed data
- Monitor resource usage and scale accordingly

### Reliability Patterns
- Implement health checks for all services
- Use load balancers for high availability
- Set up monitoring and alerting
- Plan for disaster recovery

### Cost Optimization
- Monitor token usage across all models
- Use appropriate model sizes for tasks
- Implement request deduplication
- Set up budget alerts and limits

## Troubleshooting Guide

### Common Issues
1. **API Key Errors**: Verify environment variables and key validity
2. **Token Limits**: Reduce context size or use models with larger limits
3. **Tool Call Failures**: Validate JSON schemas and parameter types
4. **Vector Search Issues**: Check embedding model consistency and data quality
5. **Performance Problems**: Profile API calls and implement caching

### Debugging Techniques
- Enable verbose logging for all components
- Test components in isolation
- Validate data at each processing step
- Use debugging tools and profilers
- Monitor network requests and responses

### Performance Tuning
- Profile embedding generation and vector searches
- Optimize batch sizes for API calls
- Implement appropriate caching strategies
- Monitor and optimize memory usage
- Use async processing for I/O operations
