## ClaudeCompat Dify Model (Usage Guide)

This extension exposes a best-effort Claude `/v1/messages` compatible endpoint
backed by Dify LLM invoke. It is not a drop-in replacement for Anthropic. This
guide documents the exact behavior, gaps, and pitfalls so consumers can use it
reliably.

### Known Differences Summary
- No structured outputs (`betas` / `output_format`) or `tools[].strict`.
- No built-in tool blocks (`server_tool_use`) or images.
- Thinking only via `<think>` or `<reasoning>` tags; `signature` is always empty.
- Citations are synthetic from `[[cite:...]]` markers only.
- Streaming events are best-effort; block boundaries may be approximate.
- Built-in web tools are mapped via `web_search_tool_result` / `web_fetch_tool_result`
  to normal tool results (no true Claude built-in events).

### Server Tools (Official, Anthropic)
According to Anthropic’s tool-use docs, **server tools** are built-in tools that
run on Anthropic’s servers and return results without client-side execution. The
officially documented server tools are:
- `web_search` (server tool)
- `web_fetch` (server tool)

Tool types are **versioned** in Anthropic APIs (e.g., `web_search_20250305`).
The docs also show versioned types for other tools such as `text_editor_20250124`
as examples of the versioning scheme.

Note: other Anthropic-defined tools like **computer use** and **text editor** are
documented as **client tools** that require client implementation, not server tools.

### Endpoint
- Method: `POST`
- Path: `/v1/messages`
- Auth: `Authorization: Bearer <api_key>` (matches plugin setting)

### Supported input (strict)
Roles:
- `user`, `assistant` only.

Content blocks (list or string):
- `text` (string or `{ "type": "text", "text": "..." }`)
- `tool_use` (assistant role only; used for tool_result tracking)
- `tool_result` (user role only; must match a prior tool_use id)
- `web_search_tool_result` (user role only; best-effort mapping, see Web Tools Mapping)
- `web_fetch_tool_result` (user role only; best-effort mapping, see Web Tools Mapping)

System field:
- `system` may be a string or a list of `text` blocks only.
- Any non-text system block returns 400.

Unsupported content blocks return 400:
- `thinking`, `redacted_thinking`, images, `server_tool_use`, or any unknown type.

Rejected request fields (400):
- `betas`, `output_format`, `tools[].strict`

Pass-through fields (best-effort):
- `temperature`, `top_p` are forwarded to Dify completion params.

Allowed models (multi-model support):
- `allowed_models` is a plugin setting that restricts which `model` values are accepted.
- Format: comma-separated list, e.g. `kimi-k2.5, kimi-k2.7`.
- If set and the request `model` is not in the list, the adapter returns 400.
- The model-selector’s settings (timeouts, max tokens, temperature, top_p, etc.) act as defaults
  for all allowed models. If the request provides `temperature`, `top_p`, or `max_tokens`,
  those override the defaults.
- `max_tokens` is optional if the model-selector default provides it; otherwise it is required.
Auto tool invocation:
- `tool_auto` (boolean): enable automatic tool execution inside the adapter.
- `tool_invocation` (object): tool routing map used when `tool_auto` is true.

### Minimal request
```json
{
  "model": "kimi-k2.5",
  "max_tokens": 128,
  "messages": [
    { "role": "user", "content": "Hello" }
  ]
}
```

### Tool use + result (required chain)
```json
{
  "model": "kimi-k2.5",
  "max_tokens": 64,
  "tools": [
    {
      "name": "get_answer",
      "description": "Get the answer",
      "input_schema": { "type": "object", "properties": {} }
    }
  ],
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
        { "type": "tool_result", "tool_use_id": "toolu_1", "content": "42" }
      ]
    }
  ]
}
```

Tooling validation details:
- `tool_use` requires `id` and `name`.
- If `tools[]` is provided, `tool_use.name` must match a declared tool.
- `tool_result` requires `tool_use_id` and must match a prior `tool_use`.
- Optional `tool_result.tool_name`/`name` is validated against the matching tool_use.
- `tool_result.content` must be a string or a list of `text` blocks only.
- `web_search_tool_result` accepts structured result objects (see Web Tools Mapping).
- `web_fetch_tool_result` accepts structured fetch objects (see Web Tools Mapping).

### Automatic tool invocation (adapter executes Dify tools)
When `tool_auto: true`, the adapter will execute tools itself if it sees a `tool_use`
block without a matching `tool_result`.

Request fields:
- `tool_auto`: `true` | `false`
- `tool_invocation`: mapping from tool name to routing info:
  - `provider_type`: `builtin` | `api` | `workflow` | `app` | `dataset-retrieval` | `mcp`
  - `provider`: provider id in Dify
  - `tool`: tool name in that provider
  - `credential_id` (optional): explicit credential id

`provider_type` meaning:
- `builtin`: Dify built-in tools (e.g. webscraper).
- `api`: API tool providers (tools connected via API in Dify Marketplace or custom).
- `workflow`: tools exposed by Dify workflows.
- `app`: tools exposed by Dify apps.
- `dataset-retrieval`: dataset retrieval tools.
- `mcp`: MCP tool providers.

How tool execution works:
- The adapter calls Dify’s tool invocation APIs via `self.session.tool`.
- It executes the tool and collects tool output messages into a single text blob.
- This text blob is injected as a `ToolPromptMessage` for the matching `tool_use` id.
- Output types handled:
  - `text`: appended as-is
  - `json`: serialized to JSON string
  - `variable`: appended as string
  - other message types are ignored unless they serialize to dicts

Credential behavior:
- If `credential_id` is provided in `tool_invocation`, it is used.
- Otherwise Dify resolves credentials from the session context (if available).

Tool provider identifiers:
- `provider` must match the provider id in Dify (e.g. `duckduckgo`).
- `tool` must match the tool name within that provider (e.g. `search`).
- If these are wrong, the adapter returns `tool invocation failed: ...`.

Default mapping:
- `web_fetch` -> `builtin` provider `webscraper`, tool `webscraper`

If `tool_auto` is enabled and a tool is not mapped, the adapter returns 400.
`web_search` has **no default mapping** and must be provided via `tool_invocation`.

Example:
```json
{
  "model": "kimi-k2.5",
  "max_tokens": 128,
  "tool_auto": true,
  "tool_invocation": {
    "web_search": {
      "provider_type": "api",
      "provider": "duckduckgo",
      "tool": "search"
    }
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

### Streaming
Set `"stream": true` to receive Claude-style SSE:
`message_start`, `content_block_start`, `content_block_delta`,
`content_block_stop`, `message_delta`, `message_stop`.

Streaming details:
- `text_delta` uses `{"type":"text_delta","text":...}`.
- `thinking_delta` uses `{"type":"thinking_delta","thinking":...}`.
- `signature_delta` is emitted with an empty signature before closing a thinking block.
- `citations_delta` are emitted one-by-one when `[[cite:...]]` markers are found.
- `input_json_delta` for tool_use is chunked (512 chars per chunk).

### Citations (best-effort)
If the model outputs `[[cite:source-id]]`, the adapter removes the marker and emits
synthetic citations. These are not backed by Dify metadata.

---

## Real Claude v1/messages vs Adapter (Gaps & Differences)

### Not supported (hard 400)
- `betas`, `output_format` (no structured outputs)
- `tools[].strict`
- `redacted_thinking`, `server_tool_use`, images

### Best-effort only
- Thinking blocks: produced only if the model outputs `<think>...</think>` or
  `<reasoning>...</reasoning>` tags.
- `signature` is always empty (cannot be verified).
- Citations are synthetic from markers; no true source metadata.
- Streaming block boundaries are best-effort (Dify streaming has no native block events).
- Tool call input is parsed from Dify tool_calls; the adapter does not invent tool calls.

### Tooling differences
- `tool_use` must be present in the assistant message to allow a later `tool_result`.
- `tool_result.tool_use_id` must match a prior tool_use id.
- If `tools[]` is provided, `tool_use.name` must match a declared tool.

### stop_reason mapping
- `length` -> `max_tokens`
- `stop_sequence` -> `stop_sequence`
- tool calls present -> `tool_use`
- else `end_turn`

---

## Common Pitfalls (and how to avoid them)

1) Missing `tool_use` before `tool_result`
   - Always send an assistant `tool_use` block before sending `tool_result`.

2) Unsupported blocks
   - Do not send `thinking`, `redacted_thinking`, images, or built-in tool blocks.

3) `betas` / `output_format` / `strict`
   - These are rejected. Remove them from client payloads.

4) Thinking not showing up
   - Only appears if the model outputs `<think>...</think>` or `<reasoning>...</reasoning>` tags.
   - Other tags (e.g. `<thought>`) are ignored and remain plain text.

5) Citations format
   - Only `[[cite:...]]` is recognized; anything else stays in the text.
6) Expecting true built-in web search events
   - `web_search_tool_result` / `web_fetch_tool_result` are mapped to normal tool
     results; no built-in web events are emitted.
7) Enabling tool_auto without a mapping
   - Provide `tool_invocation` for tools like `web_search`; otherwise 400.
8) Tool-only messages rejected upstream
   - Some upstream models reject requests without a `user` message. The adapter will
     insert a fallback user message when only tool_use/tool_result are present:
     `Use the tool results provided to answer the user.`

---

## Integration Advice (Second-Stage Development)

### Client-side adapters
- Normalize your client to treat this endpoint as "Claude-shaped" but
  "Dify-backed". Use explicit feature flags for `citations`, `thinking`, and tools.
- Add a fallback path if the server returns 400 for unsupported fields.
  A safe fallback is to drop `betas`/`output_format`/`tools[].strict` and retry.

### Testing strategy
- Always test:
  - tool_use/tool_result chain
  - streaming with `<think>` tags
  - citations marker parsing
  - rejected fields (`betas`, `output_format`, `tools[].strict`)

### Error handling
- All 4xx return Claude-style error objects:
  `{"error":{"type":"invalid_request_error","message":"..."}}`.
- Auth errors use `authentication_error`.
- Missing usage from Dify defaults to zeros in responses.

---

## Prompting Advice (to reduce surprises)

### Make thinking blocks visible
Include a system or user instruction such as:
```
Please wrap your reasoning inside <think>...</think> tags.
```
Note: the model must follow the instruction exactly.

### Make tool calls more likely
Be explicit:
```
You MUST call the tool `get_answer` with JSON input, then wait.
```
If the model does not emit tool calls, the adapter cannot invent them.

### Citations markers
If you want citations in the response, instruct:
```
When stating a claim, append [[cite:source-id]] with a stable ID.
```

---

## Exhaustive 400 Conditions (Validation Rules)

The adapter returns 400 with `invalid_request_error` for any of the following:

### Top-level request
- Missing or empty JSON body.
- Missing `model` or `max_tokens`.
- `messages` not a non-empty list.
- `betas` present (any non-empty list).
- `output_format` present (any value).
- `tool_invocation` present but not an object.

### System field
- `system` provided but not a string or a list of `text` blocks only.

### Messages and roles
- Any `role` other than `user` or `assistant`.
- `content` not a string or list of block objects.
- Any content block that is not `text`, `tool_use`, `tool_result`, `web_search_tool_result`,
  or `web_fetch_tool_result`.
- `tool_use` blocks present in `user` role messages.
- `tool_result` blocks present in `assistant` role messages.
- `web_search_tool_result` blocks present in `assistant` role messages.
- `web_fetch_tool_result` blocks present in `assistant` role messages.

### tool_use / tool_result chain
- `tool_use` missing `id` or `name`.
- `tool_use.name` not in declared `tools[]` (when `tools[]` provided).
- `tool_result` missing `tool_use_id`.
- `tool_result.tool_use_id` not matching a prior `tool_use` id.
- `tool_result.tool_name`/`name` present but not matching the matched `tool_use.name`.
- `tool_result.content` not a string or list of `text` blocks.
- `web_search_tool_result.tool_use_id` missing or not matching a prior `tool_use` id.
- `web_fetch_tool_result.tool_use_id` missing or not matching a prior `tool_use` id.
- `tool_auto` enabled with no `tool_invocation` mapping for the tool.

### Tools array
- `tools` elements not objects.
- `tools[].name` missing.
- `tools[].description` missing.
- `tools[].input_schema` missing or not an object.
- `tools[].strict == true` (unsupported).

---

## Recommended Client Handling Flow

1) Build request with only supported fields.
2) If using tools, include `tool_use` in assistant messages before any `tool_result`.
3) Send request.
4) If 400:
   - Inspect `error.message`.
   - Remove unsupported fields (`betas`, `output_format`, `tools[].strict`).
   - Ensure tool chain validity and retry.
5) If streaming:
   - Parse SSE events strictly in order.
   - Expect `citations_delta` and `signature_delta` (empty) interleaved with text/thinking deltas.

---

## Why Built-in Web Search / Server Tools Are Not Available

Dify’s LLM invoke interface does not emit Claude’s built-in tool blocks
(`server_tool_use`, `web_search_tool_result`) or the related structured metadata.
This adapter only sees text, tool calls, and tool results at the Dify layer, so it
cannot synthesize the built-in tool events without inventing data. Therefore the
adapter does not emit true built-in web search events. A best-effort mapping is
available via `web_search_tool_result` (see below), but it is still a normal tool
result under the hood.

---

## Error Message Examples (Common 400s)

Each example below is returned as:
`{"error":{"type":"invalid_request_error","message":"..."}}`

| Scenario | Example message |
|---|---|
| Missing model | `Model is required` |
| Missing max_tokens | `max_tokens is required` |
| Invalid role | `Invalid role: <role>` |
| Unsupported block type | `Unsupported content block type: <type>` |
| tool_use missing id | `tool_use.id is required` |
| tool_use missing name | `tool_use.name is required` |
| tool_result missing id | `tool_result.tool_use_id is required` |
| tool_result no match | `tool_result.tool_use_id has no matching tool_use` |
| tool strict not supported | `tool strict mode is not supported` |
| output_format not supported | `output_format is not supported` |
| betas not supported | `betas are not supported` |
| web_search_tool_result missing id | `web_search_tool_result.tool_use_id is required` |
| web_search_tool_result no match | `web_search_tool_result.tool_use_id has no matching tool_use` |
| web_fetch_tool_result missing id | `web_fetch_tool_result.tool_use_id is required` |
| web_fetch_tool_result no match | `web_fetch_tool_result.tool_use_id has no matching tool_use` |
| invalid tool_invocation | `tool_invocation must be an object` |
| tool_auto without mapping | `tool_invocation mapping required for tool_auto` |

Auth failures return:
`{"error":{"type":"authentication_error","message":"Unauthorized"}}`

---

## Typical Request/Response Patterns

### 1) Basic request (blocking)
```json
{
  "model": "kimi-k2.5",
  "max_tokens": 128,
  "messages": [
    { "role": "user", "content": "Hello" }
  ]
}
```

Response:
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "model": "kimi-k2.5",
  "content": [
    { "type": "text", "text": "Hello!" }
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": { "input_tokens": 0, "output_tokens": 0 }
}
```

### 2) Thinking request (blocking)
```json
{
  "model": "kimi-k2.5",
  "max_tokens": 128,
  "thinking": { "type": "enabled" },
  "messages": [
    { "role": "user", "content": "Explain quicksort." }
  ]
}
```

Response (only if model emits `<think>` or `<reasoning>` tags):
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
  "usage": { "input_tokens": 0, "output_tokens": 0 }
}
```

### 3) Streaming with citations markers (abridged)
```text
data: {"type":"message_start","message":{"id":"msg_...","type":"message","role":"assistant","content":[],"model":"kimi-k2.5","stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":0,"output_tokens":0}}}
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Fact "}}
data: {"type":"content_block_delta","index":0,"delta":{"type":"citations_delta","citation":{"type":"custom","reference":"src-1"}}}
data: {"type":"content_block_stop","index":0}
data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null}}
data: {"type":"message_stop"}
```

---

## Reference: Request/Response Shape (Exact)

### Blocking response (example)
```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "model": "kimi-k2.5",
  "content": [
    { "type": "thinking", "thinking": "outline steps...", "signature": "" },
    { "type": "text", "text": "Quicksort works by ...", "citations": [] }
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": { "input_tokens": 12, "output_tokens": 48 }
}
```

### Streaming event sample (abridged)
```text
data: {"type":"message_start","message":{"id":"msg_...","type":"message","role":"assistant","content":[],"model":"kimi-k2.5","stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":0,"output_tokens":0}}}

data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello "}}
data: {"type":"content_block_delta","index":0,"delta":{"type":"citations_delta","citation":{"type":"custom","reference":"src-1"}}}
data: {"type":"content_block_stop","index":0}

data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null}}
data: {"type":"message_stop"}
```

---

## Web Tools Mapping (Best-effort)

This adapter cannot emit true Claude built-in web tool events, but it can accept
`web_search_tool_result` and `web_fetch_tool_result` blocks and map them to normal
tool results. Use this when you want a Claude-like client to send web results.

### Input format (recommended)
```json
{
  "role": "assistant",
  "content": [
    { "type": "tool_use", "id": "toolu_1", "name": "web_search", "input": { "query": "..." } }
  ]
},
{
  "role": "user",
  "content": [
    {
      "type": "web_search_tool_result",
      "tool_use_id": "toolu_1",
      "content": [
        { "title": "Doc A", "snippet": "Alpha", "url": "https://a.example" },
        { "title": "Doc B", "text": "Beta", "url": "https://b.example" }
      ],
      "sources": [{ "url": "https://c.example" }]
    },
    {
      "type": "web_fetch_tool_result",
      "tool_use_id": "toolu_1",
      "content": [
        { "url": "https://a.example", "title": "Doc A", "content": "Full page text..." }
      ]
    }
  ]
}
```

### Mapping behavior
- The adapter converts result objects to plain text, appending `[[cite:<url>]]`.
- `sources` are also appended as `[[cite:...]]`.
- The resulting text is passed to Dify as a normal tool result.
- If the model echoes these markers, the adapter will emit citations.

### Limits
- No built-in Claude web tool events or metadata.
- Citation accuracy depends on your tool output formatting.
