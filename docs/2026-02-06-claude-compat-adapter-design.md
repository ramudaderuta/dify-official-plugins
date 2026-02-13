# Claude Compat Dify Model Adapter Design & Feasibility

Date: 2026-02-06

## Goal
Provide a best-effort Claude `/v1/messages` compatible endpoint backed by Dify LLM invoke. The adapter supports text and function tools, optional `<think>` parsing when `thinking.type=enabled`, and Claude-style streaming events. Unsupported Claude content block types return 400.

## Background (current plugin context)
The official Dify extension `extensions/oaicompat_dify_model` exposes `/v1/chat/completions`, parses OpenAI-style `messages`, and returns only `message.content` (no tool calls). Streaming yields only text deltas. Dify SDK supports tool calls (`AssistantPromptMessage.tool_calls`) and tool messages (`ToolPromptMessage`), but the OpenAI-compatible endpoint does not map them.

## Claude /v1/messages requirements (summary)
- `POST /v1/messages` with `model`, `max_tokens`, and `messages` list.
- `messages[].content` can be a string or list of content blocks.
- Content blocks include: `text`, `thinking`, `redacted_thinking`, `tool_use`, `tool_result`, plus built-in tool blocks (`server_tool_use`, `web_search_tool_result`).
- Streaming events include: `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`.

## Feasibility (excluding built-in tools)
### What maps cleanly
- **Basic messages**: user/assistant text → Claude `text` blocks.
- **Tool use (partial)**: Dify tool calls → Claude `tool_use` blocks.
- **Tool results (partial)**: Claude `tool_result` → Dify `ToolPromptMessage`.

### Gaps and best-effort compatibility plan
1) **Thinking / Redacted Thinking blocks**
- Gap: Dify only returns text; no structured thinking or signatures.
- Plan: If `thinking.type=enabled`, parse `<think>...</think>` tags and emit `thinking` blocks; text outside tags becomes `text` blocks.
- Limitation: `signature` cannot be produced (emit empty string).

2) **Citations and citation deltas**
- Gap: Dify responses contain no structured citation metadata.
- Plan: Do not emit citations; keep arrays empty. (Soft citation parsing can be added later if a consistent marker format is adopted.)

3) **Streaming event fidelity**
- Gap: Dify streaming has no explicit content-block boundaries or citation deltas.
- Plan: Emit best-effort block events: start a text/thinking block, stream `text_delta`/`thinking_delta`, emit empty `signature_delta` for thinking blocks, close block; emit tool_use blocks after tool calls are known via `input_json_delta`.
- Limitation: Interleaving and block boundaries are approximate.

4) **stop_reason / stop_sequence**
- Gap: Dify provides limited finish metadata.
- Plan: Map `length` → `max_tokens`, `stop_sequence` when provided, tool calls → `tool_use`, else `end_turn`. `stop_sequence` remains null unless Dify exposes it.

5) **Message content block typing**
- Gap: Dify endpoint only accepts text content.
- Plan: Accept only `text`, `tool_use`, and `tool_result` blocks; reject all others with 400.

## Scope
- New extension under `extensions/claudecompat_dify_model` (copied from `oaicompat_dify_model`).
- Endpoint path: `/v1/messages`.
- Blocking and streaming responses.
- Strict validation for unsupported blocks (images, server tool use, web search, etc.).

## Request Mapping
- `model` and `max_tokens` required.
- Optional allowlist: `allowed_models` setting in plugin. If set, reject any `model`
  not in the allowlist (comma-separated list).
- Default LLM parameters come from the model-selector configuration; request-provided
  `temperature`, `top_p`, and `max_tokens` override these defaults.
- `messages[]` roles must be `user` or `assistant`.
- `content` accepts string or list of blocks.
  - `text` blocks are concatenated.
  - `tool_use` blocks (assistant role) are accepted for tracking tool IDs and must include `id` + `name`.
  - `tool_result` blocks (user role) map to Dify `ToolPromptMessage` and must match a prior `tool_use` ID.
  - If `tools[]` is provided, `tool_use.name` must match a declared tool.
- Optional `system` field maps to `SystemPromptMessage` (string or text blocks).
- `tools[]` with `{name, description, input_schema}` maps to Dify `PromptMessageTool`.
  - `tools[].strict` is rejected (unsupported).
- `betas` and `output_format` are rejected (unsupported).

## Response Mapping
- Non-streaming: returns Claude message object with `content[]` blocks.
- `<think>...</think>` tags split into `thinking` blocks when `thinking.type=enabled`.
- Dify tool calls map to Claude `tool_use` blocks.
- Usage mapping: `input_tokens` and `output_tokens` from Dify usage.
- `stop_reason`: `tool_use` if tool calls present, else `end_turn` (with `max_tokens` when finish reason is length).
- Citations (best-effort): `[[cite:...]]` markers are stripped and emitted as synthetic citations on `text` blocks.

## Streaming
- Emit `message_start`, then `content_block_start/delta/stop` for text/thinking.
- Tool calls are emitted as `tool_use` blocks with `input_json_delta`.
- Streaming citations: `[[cite:...]]` markers are removed from text deltas and emitted as `citations_delta` one-by-one.
- `thinking_delta` uses `thinking` field; `signature_delta` is emitted with empty signature before closing a thinking block.
- End with `message_delta` and `message_stop`.

## Known Limitations
- No Claude built-in tools (server tool use / web search).
- No true citations or reasoning signatures (only synthetic citations from markers).
- No structured outputs (`betas` / `output_format`) or strict tool schema enforcement.
- Streaming is best-effort and may approximate block boundaries.
- `redacted_thinking` cannot be generated because Dify provides no reasoning redaction or signature metadata; the adapter only sees plain text and can at best split `<think>` tags.

## Enhancement Implementation Checklist (Concrete Plan)
Phased, local-only changes that keep the adapter best-effort but closer to Claude `/v1/messages`.

### Phase 1: Request Validation & Error Consistency
- Return Claude-style error shape (e.g., `{"error": {"type": "invalid_request_error", "message": "..."}}`) for all 4xx.
- Validate `messages[].content` blocks:
  - Allow `text`, `tool_use`, `tool_result` only.
  - Reject `redacted_thinking`, `server_tool_use`, `web_search_tool_result`, images, or any unknown block types.
- Enforce `tool_use`/`tool_result` chain:
  - `tool_use` allowed only in assistant role with required `id` + `name`.
  - `tool_result` allowed only in user role with `tool_use_id`.
  - `tool_result.tool_use_id` must match a prior `tool_use` id.
  - Optional: validate `tool_result` references a known tool name (if present).
- Reject unsupported request fields:
  - `betas`, `output_format`, `tools[].strict`.

### Phase 2: Response Fidelity
- Normalize response fields:
  - Always return `type: "message"`, `role: "assistant"`, `stop_sequence: null`.
  - `usage` defaults to zeros when Dify omits usage.
- `stop_reason` mapping:
  - `length` -> `max_tokens`
  - `stop_sequence` -> `stop_sequence`
  - `tool_calls` present -> `tool_use`
  - else `end_turn`

### Phase 3: Streaming Improvements
- Enforce event order:
  - `message_start` -> `content_block_*` events -> `message_delta` -> `message_stop`.
- Text vs thinking delta types:
  - `text_delta` for text blocks
  - `thinking_delta` for thinking blocks
- Robust `<think>` parsing:
  - Handle tag splits across chunks.
  - Flush trailing partial tags at stream end.
- Tool use streaming:
  - Emit `tool_use` blocks after tool calls are known, with `input_json_delta`.
  - Optional: chunk `partial_json` for large inputs.

### Phase 4: Best-effort Compatibility Extras (Optional)
- Citations (best-effort):
  - If the response contains a consistent marker (e.g., `[[cite:...]]`), parse and emit `citations`.
  - Document that citations are synthetic and not from Dify.
- `redacted_thinking` input handling:
  - Prefer explicit 400 with clear error message (avoid silently dropping content).
 - Web tools mapping (best-effort):
  - Treat Claude `web_search` / `web_fetch` requests as normal tool calls in Dify.
  - Standardize a `web_search` and `web_fetch` tool schema and map tool results to `tool_result`.
  - Convert tool outputs into citations markers (`[[cite:...]]`) to reuse the citations pipeline.
  - Explicitly document that this is not a true built-in web tool block.

### Phase 5: Tests
- Validation tests:
  - `betas`, `output_format`, `tools[].strict`, unsupported block types.
  - `tool_use`/`tool_result` chain, role constraints, missing IDs.
- Streaming tests:
  - `<think>` tag split across chunks.
  - trailing partial tag flush.
  - tool_use emission ordering.

## Implementation Status (2026-02-06)
- Phase 1: Implemented
- Phase 2: Implemented
- Phase 3: Implemented
- Phase 4: Implemented (best-effort citations markers + web_search/web_fetch mapping)
- Phase 5: Implemented

## Best-effort Web Tools Mapping (Design)

Goal: approximate Claude `web_search` / `web_fetch` built-in tools using Dify’s external data
tools or custom tool providers.

### Request-side mapping
- Client defines tools in `tools[]` named `web_search` and `web_fetch` (or configured aliases).
- Tool schema (recommended, web_search):
  - `query` (string, required)
  - `top_k` (number, optional)
  - `language` (string, optional)
  - `site` (string, optional)
- Tool schema (recommended, web_fetch):
  - `url` (string, required)
  - `user_agent` (string, optional)
- Claude request uses `tool_use` with `name: "web_search"` / `name: "web_fetch"` and `input` matching schema.

### Dify invocation
- Map `web_search` to a Dify external data tool or plugin tool.
- Invoke Dify tool and capture result text or structured output.

### Response-side mapping
- Accept `web_search_tool_result` / `web_fetch_tool_result` blocks and convert them into normal tool results.
- If tool output contains source metadata, serialize as markers:
  - `[[cite:<source-id-or-url>]]`
- Adapter citations parser will emit synthetic citations from these markers.

### Client expectations
- Clients must treat this as a normal tool call; `web_search_tool_result` /
  `web_fetch_tool_result` are only accepted as input aliases and do not produce true built-in events.
- Citations are best-effort and not first-party Claude web search citations.

### Limitations
- No built-in Claude web tool metadata.
- Citation precision depends on tool output formatting and marker correctness.

## Packaging Script
Use the helper script to package the plugin without cache artifacts:

```bash
python /home/build/code/easycheck-linux/extensions/package_claudecompat_plugin.py
```

Options:
- `--source` defaults to `extensions/claudecompat_dify_model`
- `--output` defaults to `extensions/claudecompat_dify_model.difypkg`

## References
- Claude Messages API: https://platform.claude.com/docs/en/api/messages
- Claude Messages Streaming: https://platform.claude.com/docs/en/api/messages
