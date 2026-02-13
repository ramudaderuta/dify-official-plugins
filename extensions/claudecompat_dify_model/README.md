## claudecompat_dify_model

**Author:** easycheck
**Version:** 0.0.1
**Type:** extension

### Description
Expose Dify LLMs through a best-effort Claude `/v1/messages` compatible endpoint.
Unsupported Claude content blocks (images, server tool use, web search, etc.)
return 400.

### Endpoint
`POST /v1/messages`

### Authentication
`Authorization: Bearer <api_key>` (matches the plugin setting).

### Request (blocking)
```json
{
  "model": "kimi-k2.5",
  "max_tokens": 256,
  "thinking": { "type": "enabled", "budget_tokens": 1024 },
  "messages": [
    { "role": "user", "content": "Explain quicksort." }
  ]
}
```

### Response (blocking)
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "model": "kimi-k2.5",
  "content": [
    { "type": "thinking", "thinking": "outline steps...", "signature": "" },
    { "type": "text", "text": "Quicksort works by ..." }
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": { "input_tokens": 12, "output_tokens": 48 }
}
```

### Streaming
Set `"stream": true` to receive Claude-style SSE events:
`message_start`, `content_block_start`, `content_block_delta`,
`content_block_stop`, `message_delta`, `message_stop`.
Thinking deltas use `thinking_delta` with `thinking` field, and an empty
`signature_delta` is emitted before closing a thinking block.

### Supported content blocks
Input:
- `text` (string or `{ type: "text", text: "..." }`)
- `tool_use` (assistant role only; requires `id` + `name`; used to track tool_result)
- `tool_result` (user role only; requires `tool_use_id` and must match a prior tool_use)
- `web_search_tool_result` (user role only; best-effort mapping to tool_result)
- `web_fetch_tool_result` (user role only; best-effort mapping to tool_result)

Output:
- `text`
- `thinking` (only when `thinking.type=enabled` and `<think>` tags exist)
- `tool_use` (mapped from Dify tool calls)

### Citations (best-effort)
If the model outputs markers like `[[cite:source-id]]`, the adapter removes
the marker and emits a synthetic citation. Streaming emits `citations_delta`
events one-by-one. These citations are not backed by Dify metadata.

### Web search mapping (best-effort)
`web_search_tool_result` blocks are accepted and converted into normal tool
results. If the content includes structured search results, URLs are appended
as `[[cite:...]]` markers and emitted as citations.

### Web fetch mapping (best-effort)
`web_fetch_tool_result` blocks are accepted and converted into normal tool
results. If the content includes URLs, they are appended as `[[cite:...]]` markers
and emitted as citations.

### Allowed models (multi-model support)
Set the plugin setting `allowed_models` to restrict which `model` values are
accepted. Format: comma-separated list (e.g. `kimi-k2.5, kimi-k2.7`).
Requests with other models return 400. The
model-selector settings act as defaults for all allowed models; request
`temperature`, `top_p`, or `max_tokens` override those defaults.
`max_tokens` is optional if the model-selector default provides it.

### Automatic tool invocation (tool_auto)
The adapter can call Dify tools directly when `tool_auto` is true. Provide
`tool_invocation` mapping for tool routing. Default mapping exists for `web_fetch`
(`builtin:webscraper`).

### User fallback for tool-only requests
If no `role: "user"` message exists (only tool_use/tool_result), the adapter
inserts a minimal user message to satisfy upstream model requirements:
`Use the tool results provided to answer the user.`

Example:
```json
{
  "model": "kimi-k2.5",
  "max_tokens": 128,
  "tool_auto": true,
  "tool_invocation": {
    "web_search": { "provider_type": "api", "provider": "duckduckgo", "tool": "search" }
  },
  "messages": [
    {
      "role": "assistant",
      "content": [
        { "type": "tool_use", "id": "toolu_1", "name": "web_search", "input": { "query": "Dify" } }
      ]
    }
  ]
}
```

### Tool result input example
```json
{
  "model": "kimi-k2.5",
  "max_tokens": 64,
  "messages": [
    {
      "role": "assistant",
      "content": [
        { "type": "tool_use", "id": "toolu_1", "name": "get_answer", "input": {} }
      ]
    },
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "Use the tool output." },
        { "type": "tool_result", "tool_use_id": "toolu_1", "content": "42" }
      ]
    }
  ]
}
```

### Limitations
- Unsupported input block types return 400 (images, server tools, etc.).
- `signature` for `thinking` is emitted as empty string (not verifiable).
- `redacted_thinking` cannot be produced (no Dify metadata).
- `betas`, `output_format`, and `tools[].strict` are rejected.
- Citations are best-effort markers only (no real sources).

### Packaging
Use the helper script to build a `.difypkg` without cache artifacts:
```bash
python /home/build/code/easycheck-linux/extensions/package_claudecompat_plugin.py
```
