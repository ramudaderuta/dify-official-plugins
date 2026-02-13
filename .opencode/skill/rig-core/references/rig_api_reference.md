# Rig Core: API Reference

## Agent API

### AgentBuilder

```rust
impl<M: CompletionModel> AgentBuilder<M> {
    pub fn new(model: M) -> Self
    pub fn preamble(self, preamble: &str) -> Self
    pub fn context(self, doc: &str) -> Self
    pub fn tool(self, tool: impl Tool + 'static) -> Self
    pub fn dynamic_context(self, sample: usize, index: impl VectorStoreIndexDyn + 'static) -> Self
    pub fn temperature(self, temperature: f64) -> Self
    pub fn max_tokens(self, max_tokens: u64) -> Self
    pub fn build(self) -> Agent<M>
}
```

### Agent Methods

```rust
impl<M: CompletionModel> Agent<M> {
    // High-level interfaces
    async fn prompt(&self, prompt: &str) -> Result<String, PromptError>
    async fn chat(&self, prompt: &str, history: Vec<Message>) -> Result<String, PromptError>
    
    // Low-level interface
    async fn completion(&self, prompt: &str, history: Vec<Message>) 
        -> Result<CompletionRequestBuilder<M>, CompletionError>
}
```

## Completion API

### CompletionModel Trait

```rust
trait CompletionModel {
    type Response;
    
    async fn completion(&self, request: CompletionRequest) 
        -> Result<CompletionResponse<Self::Response>, CompletionError>;
    
    fn completion_request(&self, prompt: &str) -> CompletionRequestBuilder<Self>;
}
```

### CompletionRequestBuilder

```rust
impl<M: CompletionModel> CompletionRequestBuilder<M> {
    pub fn preamble(self, preamble: String) -> Self
    pub fn temperature(self, temperature: f64) -> Self
    pub fn max_tokens(self, max_tokens: u64) -> Self
    pub fn documents(self, documents: Vec<Document>) -> Self
    pub fn tools(self, tools: Vec<ToolDefinition>) -> Self
    pub fn build(self) -> CompletionRequest
    pub async fn send(self) -> Result<CompletionResponse<M::Response>, CompletionError>
}
```

## Embeddings API

### EmbeddingModel Trait

```rust
trait EmbeddingModel {
    const MAX_DOCUMENTS: usize;
    
    fn ndims(&self) -> usize;
    
    async fn embed_document(&self, document: &str) -> Result<Embedding, EmbeddingError>;
    
    async fn embed_documents(&self, documents: impl IntoIterator<Item = String> + Send) 
        -> Result<Vec<Embedding>, EmbeddingError>;
}
```

### EmbeddingsBuilder

```rust
impl<M: EmbeddingModel> EmbeddingsBuilder<M> {
    pub fn new(model: M) -> Self
    pub fn simple_document(self, id: &str, content: &str) -> Self
    pub fn tool(self, tool: impl ToolEmbedding + 'static) -> Result<Self, EmbeddingError>
    pub async fn build(self) -> Result<Embeddings, EmbeddingError>
}
```

## Tools API

### Tool Trait

```rust
trait Tool: Send + Sync {
    const NAME: &'static str;
    type Error: std::error::Error + Send + Sync + 'static;
    type Args: for<'a> Deserialize<'a> + Send + Sync;
    type Output: Serialize;
    
    fn name(&self) -> String { Self::NAME.to_string() }
    
    async fn definition(&self, prompt: String) -> ToolDefinition;
    async fn call(&self, args: Self::Args) -> Result<Self::Output, Self::Error>;
}
```

### ToolSet

```rust
impl ToolSet {
    pub fn from_tools(tools: Vec<impl ToolDyn + 'static>) -> Self
    pub fn add_tool(&mut self, tool: impl ToolDyn + 'static)
    pub async fn call(&self, toolname: &str, args: String) -> Result<String, ToolSetError>
    pub fn contains(&self, toolname: &str) -> bool
}
```

## Vector Store API

### VectorStore Trait

```rust
trait VectorStore {
    type Q;
    
    async fn add_documents(&mut self, documents: Vec<DocumentEmbeddings>) 
        -> Result<(), VectorStoreError>;
    
    async fn get_document(&self, id: &str) 
        -> Result<Option<DocumentEmbeddings>, VectorStoreError>;
}
```

### VectorStoreIndex Trait

```rust
trait VectorStoreIndex {
    async fn top_n<T: for<'a> Deserialize<'a> + Send>(
        &self, 
        query: &str, 
        n: usize
    ) -> Result<Vec<(f64, String, T)>, VectorStoreError>;
    
    async fn top_n_ids(&self, query: &str, n: usize) 
        -> Result<Vec<(f64, String)>, VectorStoreError>;
}
```

## Provider Clients

### OpenAI

```rust
impl openai::Client {
    pub fn new(api_key: &str) -> Self
    pub fn from_env() -> Self
    pub fn completion_model(&self, model: &str) -> openai::CompletionModel
    pub fn embedding_model(&self, model: &str) -> openai::EmbeddingModel
    pub fn agent(&self, model: &str) -> AgentBuilder<openai::CompletionModel>
}

// Available models
pub const GPT_4O: &str = "gpt-4o";
pub const GPT_4: &str = "gpt-4";
pub const TEXT_EMBEDDING_ADA_002: &str = "text-embedding-ada-002";
```

### Cohere

```rust
impl cohere::Client {
    pub fn new(api_key: &str) -> Self
    pub fn from_env() -> Self
    pub fn completion_model(&self, model: &str) -> cohere::CompletionModel
    pub fn embedding_model(&self, model: &str) -> cohere::EmbeddingModel
}

// Available models
pub const COMMAND_R: &str = "command-r";
pub const EMBED_ENGLISH_V3: &str = "embed-english-v3.0";
```

## Error Types

### CompletionError

```rust
#[derive(Debug, thiserror::Error)]
pub enum CompletionError {
    #[error("HttpError: {0}")]
    HttpError(#[from] reqwest::Error),
    
    #[error("JsonError: {0}")]
    JsonError(#[from] serde_json::Error),
    
    #[error("RequestError: {0}")]
    RequestError(String),
    
    #[error("ResponseError: {0}")]
    ResponseError(String),
}
```

### ToolSetError

```rust
#[derive(Debug, thiserror::Error)]
pub enum ToolSetError {
    #[error("ToolNotFoundError: {0}")]
    ToolNotFoundError(String),
    
    #[error("ToolCallError: {0}")]
    ToolCallError(#[from] ToolError),
}
```

## File Loaders

### FileLoader

```rust
impl<'a> FileLoader<'a, std::fs::File> {
    pub fn with_glob(pattern: &'a str) -> Result<Self, LoaderError>
    pub fn with_dir(dir: &'a str) -> Result<Self, LoaderError>
    pub fn read(self) -> impl Iterator<Item = Result<String, LoaderError>>
    pub fn read_with_path(self) -> impl Iterator<Item = Result<(PathBuf, String), LoaderError>>
    pub fn ignore_errors(self) -> Self
}
```

### PdfFileLoader (requires "pdf" feature)

```rust
impl<'a> PdfFileLoader<'a, std::fs::File> {
    pub fn with_glob(pattern: &'a str) -> Result<Self, LoaderError>
    pub fn load(self) -> impl Iterator<Item = Result<String, LoaderError>>
    pub fn by_page(self) -> Self
}
```
