# Dify Chat App API (Clean English Reference)

Source: TEST-OOKOO platform dev page (Chat App API)

---

## Basics

- Base URL: `https://test-ookoo.is.panasonic.cn/v1`
- Auth header: `Authorization: Bearer {API_KEY}`
- Security: store API keys on the server side to avoid leakage

---

## Send Chat Message

**POST** `/chat-messages`

### Request Body

| Field | Type | Description |
|---|---|---|
| `query` | string | User input/question |
| `inputs` | object | App-defined variables, default `{}` |
| `response_mode` | string | `streaming` (SSE, recommended) or `blocking` (wait for full response). Blocking can be cut off after 100s due to Cloudflare. **Agent mode does not allow `blocking`.** |
| `user` | string | User identifier, must be unique within the app |
| `conversation_id` | string | Optional. Continue a previous conversation |
| `files` | array[object] | Optional. File inputs (requires model with Vision/Video) |
| `auto_generate_name` | bool | Optional. Auto-generate conversation title (default `true`) |
| `workflow_id` | string | Optional. Specific workflow version ID |
| `trace_id` | string | Optional. Trace ID (priority: Header `X-Trace-Id` > Query `trace_id` > Body `trace_id`) |

### files Item Fields

| Field | Type | Description |
|---|---|---|
| `type` | string | `document` / `image` / `audio` / `video` / `custom` |
| `transfer_method` | string | `remote_url` / `local_file` |
| `url` | string | Required if `transfer_method=remote_url` |
| `upload_file_id` | string | Required if `transfer_method=local_file` |

**Supported file types**

- document: `TXT`, `MD`, `MARKDOWN`, `MDX`, `PDF`, `HTML`, `XLSX`, `XLS`, `VTT`, `PROPERTIES`, `DOC`, `DOCX`, `CSV`, `EML`, `MSG`, `PPTX`, `PPT`, `XML`, `EPUB`
- image: `JPG`, `JPEG`, `PNG`, `GIF`, `WEBP`, `SVG`
- audio: `MP3`, `M4A`, `WAV`, `WEBM`, `MPGA`
- video: `MP4`, `MOV`, `MPEG`, `WEBM`

---

## Response (Blocking)

`Content-Type: application/json`

**ChatCompletionResponse fields**

- `event`: fixed `message`
- `task_id`: task identifier (used by stop endpoint)
- `id`: unique id
- `message_id`: message id
- `conversation_id`: conversation id
- `mode`: fixed `chat`
- `answer`: full answer text
- `metadata`:
  - `usage`: token usage and cost
  - `retriever_resources`: reference segments (if any)
- `created_at`: timestamp

---

## Response (Streaming / SSE)

`Content-Type: text/event-stream`

Each SSE chunk starts with `data: {json}` and chunks are separated by `\n\n`.

### Event Types

**`message`** (basic assistant chunk)
- `task_id`, `message_id`, `conversation_id`, `answer`, `created_at`

**`agent_message`** (Agent mode chunk)
- `task_id`, `message_id`, `conversation_id`, `answer`, `created_at`

**`agent_thought`** (Agent reasoning/tool call details)
- `id`, `task_id`, `message_id`, `position`, `thought`, `observation`, `tool`, `tool_input`, `created_at`, `message_files`, `conversation_id`

**`message_file`** (new file available)
- `id`, `type`, `belongs_to`, `url`, `conversation_id`

**`message_end`** (end of stream)
- `task_id`, `message_id`, `conversation_id`, `metadata`

**`tts_message`** (audio chunk, base64)
- `task_id`, `message_id`, `audio`, `created_at`

**`tts_message_end`** (end of TTS stream)
- `task_id`, `message_id`, `audio`, `created_at`

**`message_replace`** (content moderation replacement)
- `task_id`, `message_id`, `conversation_id`, `answer`, `created_at`

**`error`** (stream error)
- `task_id`, `message_id`, `status`, `code`, `message`

**`ping`** (keep-alive every ~10s)

---

## Errors (Chat)

- `404` conversation not found
- `400` `invalid_param`
- `400` `app_unavailable`
- `400` `provider_not_initialize`
- `400` `provider_quota_exceeded`
- `400` `model_currently_not_support`
- `400` `workflow_not_found`
- `400` `draft_workflow_error`
- `400` `workflow_id_format_error`
- `400` `completion_request_error`
- `500` internal server error

---

## Example Request (Streaming)

```bash
curl -X POST 'https://test-ookoo.is.panasonic.cn/v1/chat-messages' \
  -H 'Authorization: Bearer {api_key}' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "inputs": {},
    "query": "What are the specs of the iPhone 13 Pro Max?",
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "abc-123",
    "files": [
      {
        "type": "image",
        "transfer_method": "remote_url",
        "url": "https://cloud.dify.ai/logo/logo-site.png"
      }
    ]
  }'
```

---

## Conversations

### List Conversations

**GET** `/conversations`

Query parameters:

| Field | Type | Description |
|---|---|---|
| `user` | string | User identifier (unique in app) |
| `last_id` | string | Optional paging cursor |
| `limit` | int | Optional, 1-100, default 20 |
| `sort_by` | string | Optional: `created_at`, `-created_at`, `updated_at`, `-updated_at` |

Response list item fields:

- `id`, `name`, `inputs`, `status`, `introduction`, `created_at`, `updated_at`
- `has_more`, `limit`

### Delete Conversation

**DELETE** `/conversations/{conversation_id}`

Request body:

| Field | Type | Description |
|---|---|---|
| `user` | string | User identifier |

Response: `204 No Content`

### Rename Conversation

**POST** `/conversations/{conversation_id}/name`

Request body:

| Field | Type | Description |
|---|---|---|
| `name` | string | Optional name (omit if auto-generate) |
| `auto_generate` | bool | Optional, default `false` |
| `user` | string | User identifier |

Response fields: `id`, `name`, `inputs`, `status`, `created_at`, `updated_at`

---

## Conversation Variables

### Get Variables

**GET** `/conversations/{conversation_id}/variables`

Query parameters:

| Field | Type | Description |
|---|---|---|
| `user` | string | User identifier |
| `last_id` | string | Optional paging cursor |
| `limit` | int | Optional, 1-100 |
| `variable_name` | string | Optional, filter by name |

Response fields:

- `limit`, `has_more`, `data[]`
- `data[]` item: `id`, `name`, `value_type`, `value`, `description`, `created_at`, `updated_at`

### Update Variable

**PUT** `/conversations/{conversation_id}/variables/{variable_id}`

Request body:

| Field | Type | Description |
|---|---|---|
| `value` | any | New value (must match expected type) |
| `user` | string | User identifier |

Errors:

- `400` type mismatch
- `404` `conversation_not_exists`
- `404` `conversation_variable_not_exists`

---

## Audio

### Speech-to-Text

**POST** `/audio-to-text` (multipart/form-data)

- `file`: audio file (`mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `wav`, `webm`), ≤ 15 MB
- `user`: user identifier

Response:

```json
{ "text": "hello" }
```

### Text-to-Speech

**POST** `/text-to-audio` (multipart/form-data)

- `message_id`: preferred (uses Dify-generated content)
- `text`: used if `message_id` not provided
- `user`: user identifier

Response headers: `Content-Type: audio/wav`

---

## App Info

### Get App Info

**GET** `/info`

Returns: `name`, `description`, `tags`, `mode`, `author_name`

### Get App Parameters

**GET** `/parameters`

Returns:

- `opening_statement`
- `suggested_questions`
- `suggested_questions_after_answer.enabled`
- `speech_to_text.enabled`
- `text_to_speech.enabled`, `voice`, `language`, `autoPlay`
- `retriever_resource.enabled`
- `annotation_reply.enabled`
- `user_input_form` (input schema)
- `file_upload` (per-type settings)
- `system_parameters` (file size limits)

**user_input_form controls**

- `text-input`: `label`, `variable`, `required`, `max_length`, `default`
- `paragraph`: `label`, `variable`, `required`, `default`
- `select`: `label`, `variable`, `required`, `default`, `options`

**file_upload per type** (`document`, `image`, `audio`, `video`, `custom`)

- `enabled`
- `number_limits`
- `transfer_methods` (`remote_url`, `local_file`)

**system_parameters**

- `file_size_limit`, `image_file_size_limit`, `audio_file_size_limit`, `video_file_size_limit`

### Get App Meta

**GET** `/meta`

Returns:

- `tool_icons`: map of tool name to icon (URL or `{ background, content }`)

### Get WebApp Settings

**GET** `/site`

Returns:

- `title`, `chat_color_theme`, `chat_color_theme_inverted`
- `icon_type` (`emoji` / `image`)
- `icon`, `icon_background`, `icon_url`
- `description`, `copyright`
- `privacy_policy`, `custom_disclaimer`
- `default_language`
- `show_workflow_steps`
- `use_icon_as_answer_icon`

---

## Notes

- Agent mode does not support `blocking`.
- Use `response_mode=streaming` for Agent Chat Apps.
- Keep API keys server-side.

