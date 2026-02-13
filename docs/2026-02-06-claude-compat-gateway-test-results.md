# Claude Compat Gateway Test Results

Date: 2026-02-06

## Endpoint
- URL: https://test-ookoo-platform.is.panasonic.cn/e/0yniey3axwuldbdw/v1/messages
- Auth: `Authorization: Bearer password`
- Model: `glm-4.7`

## Summary (Updated After Adapter Enhancements)
- **Baseline**: Works for both `kimi-k2.5` and `glm-4.7` (text response).
- **Thinking blocks**: Produced when model outputs `<think>` or `<reasoning>` tags.
- **Tool use**: Tool results accepted; adapter inserts fallback user text if only tool_use/tool_result are present.
- **Web search / fetch mapping**: `web_search_tool_result` and `web_fetch_tool_result` are accepted and mapped to normal tool results with synthetic citations.
- **Streaming**: Works and returns Claude-style SSE events (message/content block sequence).

## Test Cases & Observations

### 1) baseline
Request: simple `ping` user message.
Result: **200**, response contains `content: [{type: "text"}]`.

### 2) thinking_required_tag
Request: `thinking.type=enabled` and prompt asks for `<think>...</think>`.
Result: **200**, thinking block produced when `<think>` or `<reasoning>` tags are emitted.

### 3) thinking_json_format
Request: stronger prompt for `<think>` tags.
Result: **200**, model emitted `<reasoning>` and adapter produced a `thinking` block.

### 4) tool_use_force
Request: tool_use + tool_result chain (assistant tool_use, user tool_result).
Result: **200**, adapter inserts fallback user text if needed and model responds.

### 5) tool_use_force_json
Request: web_search_tool_result mapping with structured results.
Result: **200**, response contains synthetic citations from result URLs.

### 6) tool_result_input
Request: web_fetch_tool_result mapping with structured content.
Result: **200**, response contains synthetic citations from URLs.

### 7) streaming_text
Request: `stream: true` with simple prompt.
Result: **200**, Claude-style SSE events (`message_start`, `content_block_delta`, `message_stop`).

## Conclusions
- Adapter logic is working with enhanced parsing and fallback behavior.
- `thinking` blocks appear when `<think>` or `<reasoning>` tags are present.
- Tool results can be provided via tool_use/tool_result chain; adapter inserts a fallback user message when needed.
- Web search/fetch tool results are mapped to normal tool results with synthetic citations.

## Recommended Next Steps
- Test with a model that supports tool calling and is configured to do so.
- If desired, extend the adapter to accept assistant `tool_use` blocks and inject synthetic tool calls before tool results.
