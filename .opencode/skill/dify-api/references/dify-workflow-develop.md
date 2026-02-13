# Dify Workflow App API (Clean English Reference)

Source: TEST-OOKOO platform dev page (Workflow App API)

---

## Overview

- Workflow apps do **not** support conversations (sessionless).
- Suitable for translation, writing, summarization, etc.

---

## Basics

- Base URL: `https://test-ookoo.is.panasonic.cn/v1`
- Auth header: `Authorization: Bearer {API_KEY}`
- Security: keep API keys on the server side

---

## Run Workflow (Latest Published)

**POST** `/workflows/run`

### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `inputs` | object | Yes | App-defined variables. Can include file-list variables |
| `response_mode` | string | Yes | `streaming` (SSE) or `blocking` |
| `user` | string | Yes | End-user identifier (must be unique in app) |
| `files` | array[object] | No | Optional file list |
| `trace_id` | string | No | Trace ID (Header `X-Trace-Id` > Query `trace_id` > Body `trace_id`) |

### File Item Structure (for file-list variables)

| Field | Type | Description |
|---|---|---|
| `type` | string | `document` / `image` / `audio` / `video` / `custom` |
| `transfer_method` | string | `remote_url` / `local_file` |
| `url` | string | Required if `remote_url` |
| `upload_file_id` | string | Required if `local_file` |

**Supported types**

- document: `TXT`, `MD`, `MARKDOWN`, `MDX`, `PDF`, `HTML`, `XLSX`, `XLS`, `VTT`, `PROPERTIES`, `DOC`, `DOCX`, `CSV`, `EML`, `MSG`, `PPTX`, `PPT`, `XML`, `EPUB`
- image: `JPG`, `JPEG`, `PNG`, `GIF`, `WEBP`, `SVG`
- audio: `MP3`, `M4A`, `WAV`, `WEBM`, `AMR`
- video: `MP4`, `MOV`, `MPEG`, `MPGA`

---

## Run Specific Workflow Version

**POST** `/workflows/{workflow_id}/run`

Path parameter:

| Field | Type | Description |
|---|---|---|
| `workflow_id` | string | Workflow version ID (from version history copy icon) |

Request/response structure is the same as `/workflows/run`.

---

## Response (Blocking)

`Content-Type: application/json`

Top-level fields:

- `workflow_run_id`: workflow run id
- `task_id`: task id (used to stop streaming runs)
- `data`: details

`data` fields:

- `id`, `workflow_id`
- `status`: `running` / `succeeded` / `failed` / `stopped`
- `outputs` (optional)
- `error` (optional)
- `elapsed_time` (s, optional)
- `total_tokens` (optional)
- `total_steps` (optional)
- `created_at`, `finished_at`

---

## Response (Streaming / SSE)

`Content-Type: text/event-stream`

Events include:

**`workflow_started`**
- `task_id`, `workflow_run_id`, `data.id`, `data.workflow_id`, `data.created_at`

**`node_started`**
- `task_id`, `workflow_run_id`, `data.node_id`, `data.node_type`, `data.title`, `data.index`, `data.predecessor_node_id`, `data.inputs`, `data.created_at`

**`text_chunk`**
- `task_id`, `workflow_run_id`, `data.text`, `data.from_variable_selector`

**`node_finished`**
- `task_id`, `workflow_run_id`
- `data.outputs`, `data.status`, `data.error`, `data.elapsed_time`
- `data.execution_metadata.total_tokens`, `data.execution_metadata.total_price`, `data.execution_metadata.currency`

**`workflow_finished`**
- `task_id`, `workflow_run_id`
- `data.outputs`, `data.status`, `data.error`, `data.elapsed_time`, `data.total_tokens`, `data.total_steps`, `data.created_at`, `data.finished_at`

**`tts_message`**, **`tts_message_end`**

**`ping`** (keep-alive)

---

## Errors (Run)

- `400` `invalid_param`
- `400` `app_unavailable`
- `400` `provider_not_initialize`
- `400` `provider_quota_exceeded`
- `400` `model_currently_not_support`
- `400` `workflow_request_error`
- `500` internal error

---

## Get Workflow Run Status

**GET** `/workflows/run/{workflow_run_id}`

Response fields:

- `id`, `workflow_id`, `status`
- `inputs`, `outputs`, `error`
- `total_steps`, `total_tokens`
- `created_at`, `finished_at`, `elapsed_time`

---

## Stop Workflow Task (Streaming Only)

**POST** `/workflows/tasks/{task_id}/stop`

Request body:

| Field | Type | Description |
|---|---|---|
| `user` | string | Must match the `user` used in run request |

Response:

```json
{ "result": "success" }
```

---

## File Upload

**POST** `/files/upload` (multipart/form-data)

Fields:

- `file`: file content
- `user`: end-user identifier

Response fields:

- `id`, `name`, `size`, `extension`, `mime_type`, `created_by`, `created_at`

Errors:

- `400` `no_file_uploaded`
- `400` `too_many_files`
- `400` `unsupported_preview`
- `400` `unsupported_estimate`
- `413` `file_too_large`
- `415` `unsupported_file_type`
- `503` `s3_connection_failed`
- `503` `s3_permission_denied`
- `503` `s3_file_too_large`

---

## Workflow Logs

**GET** `/workflows/logs`

Query parameters:

| Field | Type | Description |
|---|---|---|
| `keyword` | string | Keyword filter |
| `status` | string | `succeeded` / `failed` / `stopped` |
| `page` | int | Page number (default 1) |
| `limit` | int | Page size (default 20) |
| `created_by_end_user_session_id` | string | End-user session id |
| `created_by_account` | string | Creator account (email) |

Response fields:

- `page`, `limit`, `total`, `has_more`
- `data[]` with `workflow_run` info and creator metadata

---

## App Info

**GET** `/info`

Returns:

- `name`, `description`, `tags`, `mode`, `author_name`

---

## App Parameters

**GET** `/parameters`

Returns:

- `user_input_form` (input schema)
- `file_upload` settings
- `system_parameters` (file size limits)

`user_input_form` controls:

- `text-input`: `label`, `variable`, `required`, `default`
- `paragraph`: `label`, `variable`, `required`, `default`
- `select`: `label`, `variable`, `required`, `default`, `options`

`file_upload` per type (`document`, `image`, `audio`, `video`, `custom`):

- `enabled`, `number_limits`, `transfer_methods`

`system_parameters`:

- `file_size_limit`, `image_file_size_limit`, `audio_file_size_limit`, `video_file_size_limit`

---

## WebApp Settings

**GET** `/site`

Returns:

- `title`, `icon_type`, `icon`, `icon_background`, `icon_url`
- `description`, `copyright`
- `privacy_policy`, `custom_disclaimer`
- `default_language`, `show_workflow_steps`

