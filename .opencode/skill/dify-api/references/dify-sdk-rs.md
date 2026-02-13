# dify-sdk-rs (dify-client) Quick Start Guide

**Use Case:** Directly invoke the official Dify API within EasyCheck's Rig adapter layer, rather than going through the OpenAI compatibility layer. This guide is based on the `rming/dify-sdk-rs` (crate `dify-client` 0.3.1) source code.

## Installation & Features
```toml
[dependencies]
dify-client = "0.3.1"          # Keep default features for built-in TLS
# Or use rustls to avoid native TLS:
dify-client = { version = "0.3.1", default-features = false, features = ["rustls-tls"] }
```
Main dependencies: `reqwest` (json/multipart/stream), `eventsource-stream` (SSE), `serde_with`, `bytes`, `anyhow`, `infer`.

## Core Types
- `Config { base_url, api_key, timeout }`
- `Client::new(base_url, api_key)` / `Client::new_with_config(config)`
- `Api<'a>` obtained via `client.api()`
- Request types: `ChatMessagesRequest`, `CompletionMessagesRequest`, `WorkflowsRunRequest`, `FilesUploadRequest`, `AudioToTextRequest`, `TextToAudioRequest`, `StreamTaskStopRequest`, etc.
- Response types: `ChatMessagesResponse`, `CompletionMessagesResponse`, `WorkflowsRunResponse`, `FilesUploadResponse`, `MetaResponse`, `ParametersResponse`, `ResultResponse`
- Streaming wrapper: `SseMessageEventStream<T: Stream<Item = Result<Bytes, reqwest::Error>>>`
- Enums: `ResponseMode::{Streaming, Blocking}`, `AppMode`

## Basic Usage (Blocking/One-shot)
```rust
use dify_client::{request, ApiPath, Client, Config};
use std::time::Duration;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = Config {
        base_url: "https://api.dify.ai".into(),
        api_key: "app-xxxx".into(),
        timeout: Duration::from_secs(60),
    };
    let client = Client::new_with_config(config);
    let api = client.api();

    let req = request::ChatMessagesRequest {
        query: "Hello, please summarize today's news".into(),
        user: "user-1".into(),
        ..Default::default()
    };
    let resp = api.chat_messages(req).await?;
    println!("{:#?}", resp);
    Ok(())
}
```

## Streaming Chat / Workflow / Completion
The SDK has built-in SSE handling and automatically sets `response_mode` to `Streaming`:
```rust
use dify_client::{request, Client};
use futures::StreamExt;

let client = Client::new("https://api.dify.ai", "app-xxxx");
let api = client.api();
let mut stream = api.chat_messages_stream(request::ChatMessagesRequest {
    query: "Tell me a joke".into(),
    user: "u1".into(),
    ..Default::default()
}).await?;

while let Some(evt) = stream.next().await {
    match evt {
        Ok(msg) => println!("event: {:?}", msg),
        Err(e) => eprintln!("stream err: {e}"),
    }
}
```
Additional methods available:
- `workflows_run_stream(WorkflowsRunRequest)`
- `completion_messages_stream(CompletionMessagesRequest)`
- Stop operations: `chat_messages_stop(StreamTaskStopRequest { task_id })` / `workflows_stop` / `completion_messages_stop`

## File Upload
`FilesUploadRequest { file: impl Read + Send + Sync + 'static, mime_type: Option<String> }`
The SDK uses `multipart` and `infer` to automatically detect MIME type, returning `FilesUploadResponse` (containing `id`), which can be referenced in subsequent chat requests via `inputs`.

## Other Common APIs
- `parameters(ParametersRequest)`: Get application parameter definitions
- `meta(MetaRequest)`: Get app meta/icon
- `conversations` series: `conversations`, `conversations_delete`, `conversations_rename`
- `messages` series: `messages`, `messages_feedbacks`, `messages_suggested`
- Audio: `audio_to_text`, `text_to_audio`

## Hooks / Reusability
- `Api::before_send(|req| { ...; req })` allows modifying headers before sending (e.g., dynamically replacing API key or injecting trace-id).
- `Client` internally holds `reqwest::Client`, which can be cloned across threads; `Config::timeout` applies to all requests.

## Integration Recommendations for EasyCheck / Rig
- Directly reuse the SDK source code synchronized under the `src-tauri/src/dify` directory to avoid external crate version drift.
- Use a unified trait to abstract `send_chat`, `send_completion`, `run_workflow`, `upload_file`, `stop_task`, delegating to corresponding `Api` methods in the implementation; streaming functions output `SseMessageEventStream`.
- Choose `rustls-tls` to reduce Windows OpenSSL dependencies; if proxy is needed, apply existing `reqwest` client configuration strategy.

