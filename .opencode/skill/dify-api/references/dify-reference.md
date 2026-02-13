# Dify API Reference Documentation

This document contains reference information extracted from the official Dify documentation via Context7.

## Table of Contents

1. [API Access Configuration](#api-access-configuration)
2. [Chat Messages API](#chat-messages-api)
3. [Dataset Management](#dataset-management)
4. [API Extensions](#api-extensions)

---

## API Access Configuration

### Server Address (Base URL)

API request base URLs vary depending on your Dify deployment:

**Dify Cloud (SaaS)**:
```
https://api.dify.ai/v1
```

**Local/Private Deployment**:
```
http://localhost/v1
```

### API Key (Authentication)

Each Dify application has its own dedicated API key for authentication and authorization.

**How to get API Key**:
- Navigate to your Dify application's Overview, Access API, or Monitoring page
- Click "API Keys" to manage or generate keys

**Usage**:
Add the API key to HTTP request headers as follows:
```
Authorization: Bearer YOUR_API_KEY
```

**Security Warning**:
- API keys have high privileges for accessing application data
- **NEVER** hardcode or expose keys in client-side code (browsers, mobile apps)
- Store keys in secure server-side environments
- Proxy Dify API calls through your backend service

**Access Control**:
In the application's **Monitoring → Backend Service API** settings, you can:
- Manage API access status
- Temporarily disable all API calls if needed

---

## Chat Messages API

### Endpoint
```
POST /v1/chat-messages
```

### Purpose
Send chat messages to a Dify application and receive AI responses. Supports conversation continuity via `conversation_id`.

### Request Format

**Headers**:
```
Authorization: Bearer {api_key}
Content-Type: application/json
```

**Body**:
```json
{
    "inputs": {},
    "query": "Your question here",
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "user-identifier"
}
```

**Parameters**:
- `inputs` (object): Additional input variables as key-value pairs
- `query` (string): The user's question or message
- `response_mode` (string): Response mode - "streaming" or "blocking"
  - **Note**: Agent Chat Apps only support "streaming" mode
- `conversation_id` (string): Leave empty for new conversations; provide ID to continue existing conversation
- `user` (string): Unique user identifier for tracking

### Response Format (Streaming)

The API returns Server-Sent Events (SSE) with the following event types:

**agent_message** - Incremental message chunks:
```json
{
    "event": "agent_message",
    "conversation_id": "xxx",
    "message_id": "xxx",
    "answer": "text chunk",
    "created_at": 1234567890
}
```

**agent_thought** - Agent's reasoning (if available):
```json
{
    "event": "agent_thought",
    "thought": "reasoning text",
    "position": 1
}
```

**message_end** - Final message with metadata:
```json
{
    "event": "message_end",
    "metadata": {
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 42,
            "total_tokens": 57,
            "total_price": "0.000095",
            "currency": "RMB",
            "latency": 2.134
        }
    }
}
```

### Examples

**cURL**:
```bash
curl --location --request POST 'https://api.dify.ai/v1/chat-messages' \
--header 'Authorization: Bearer ENTER-YOUR-SECRET-KEY' \
--header 'Content-Type: application/json' \
--data-raw '{
    "inputs": {},
    "query": "Hello",
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "abc-123"
}'
```

**Python**:
```python
import requests
import json

url = 'https://api.dify.ai/v1/chat-messages'
headers = {
    'Authorization': 'Bearer ENTER-YOUR-SECRET-KEY',
    'Content-Type': 'application/json',
}
data = {
    "inputs": {},
    "query": "Hello",
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "abc-123"
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.text)
```

### Important Notes

1. **Conversation Isolation**: Conversations created via Service API are separate from WebApp conversations
2. **New Conversations**: Leave `conversation_id` empty; system will generate and return new ID
3. **Continuing Conversations**: Use the `conversation_id` from previous response
4. **Agent Apps**: Only support `response_mode: "streaming"` (blocking mode will return error)

---

## Parameters API

### Endpoint
```
GET /v1/parameters
```

### Purpose
Retrieve application configuration and capabilities.

### Response Format

```json
{
  "opening_statement": "",
  "suggested_questions": [],
  "suggested_questions_after_answer": {
    "enabled": false
  },
  "speech_to_text": {
    "enabled": false
  },
  "text_to_speech": {
    "enabled": false,
    "voice": "",
    "language": ""
  },
  "retriever_resource": {
    "enabled": false
  },
  "annotation_reply": {
    "enabled": false
  },
  "file_upload": {
    "enabled": false,
    "allowed_file_types": [],
    "allowed_file_extensions": [".JPG", ".JPEG", ".PNG", ...],
    "number_limits": 3
  },
  "system_parameters": {
    "image_file_size_limit": 50,
    "video_file_size_limit": 50,
    "audio_file_size_limit": 50,
    "file_size_limit": 50
  }
}
```

---

## Conversations API

### Endpoint
```
GET /v1/conversations
```

### Purpose
Retrieve list of conversations for the current user.

### Response Format

```json
{
  "data": [
    {
      "id": "conversation-id",
      "created_at": 1234567890,
      "status": "active",
      "summary": "Conversation summary"
    }
  ]
}
```

---

## Dataset Management APIs

### Create Document by Text

**Endpoint**: `POST /v1/datasets/{dataset_id}/document/create_by_text`

**Purpose**: Create a knowledge base document using plain text content.

**Request**:
```bash
curl --location --request POST 'https://api.dify.ai/v1/datasets/{dataset_id}/document/create_by_text' \
--header 'Authorization: Bearer {api_key}' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "document-name",
    "text": "document content",
    "indexing_technique": "high_quality",
    "process_rule": {
        "mode": "automatic"
    }
}'
```

### Dataset Metadata APIs

#### Add Metadata Field
```
POST /v1/datasets/{dataset_id}/metadata
```

#### Update Metadata Field
```
PATCH /v1/datasets/{dataset_id}/metadata/{metadata_id}
```

#### Delete Metadata Field
```
DELETE /v1/datasets/{dataset_id}/metadata/{metadata_id}
```

#### Get Metadata List
```
GET /v1/datasets/{dataset_id}/metadata
```

---

## API Extensions

### API Verification (Ping/Pong)

When configuring API-based extensions, Dify sends a verification request:

**Request**:
```json
{
    "point": "ping"
}
```

**Expected Response**:
```json
{
    "result": "pong"
}
```

### FastAPI Example

```python
from fastapi import FastAPI, Body, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

class InputData(BaseModel):
    point: str
    params: dict = {}

@app.post("/api/dify/receive")
async def dify_receive(data: InputData = Body(...), authorization: str = Header(None)):
    """
    Receive API query data from Dify.
    """
    expected_api_key = "123456"  # Your API key
    auth_scheme, _, api_key = authorization.partition(' ')

    if auth_scheme.lower() != "bearer" or api_key != expected_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    point = data.point

    if point == "ping":
        return {"result": "pong"}

    if point == "app.external_data_tool.query":
        return handle_query(params=data.params)

    raise HTTPException(status_code=400, detail="Not implemented")

def handle_query(params: dict):
    # Your implementation here
    return {"result": "query result"}
```

---

## Interactive API Testing

Most API endpoint documentation pages include a "Try It" feature:

1. **Locate 'Try It' function**: Usually at the top or right side of the page
2. **Configure parameters**:
   - Server address (Base URL)
   - Authentication (API Key)
   - Path and query parameters
   - Request body (for POST/PUT/PATCH)
3. **Send request**: Click "Send" or "Execute"
4. **View results**: See HTTP status, headers, and response body

---

## Key Differences from OpenAI API

| Feature | OpenAI API | Dify API |
|---------|------------|----------|
| **Endpoint** | `/v1/chat/completions` | `/v1/chat-messages` |
| **Request Format** | `messages` array | `query` + `inputs` |
| **Response Mode** | `stream` (boolean) | `response_mode` (string) |
| **Model Selection** | `model` parameter | Pre-configured in app |
| **API Key Format** | `Bearer sk-...` | `Bearer app-...` |
| **Conversation** | Managed in messages | `conversation_id` |

---

## Error Codes and Troubleshooting

### Common Errors

**401 Unauthorized**:
- Invalid or missing API key
- Expired API key
- Incorrect authorization header format

**400 Bad Request**:
- Invalid request format
- Missing required parameters
- "Agent Chat App does not support blocking mode" - Use streaming mode

**404 Not Found**:
- Incorrect endpoint URL
- Resource (conversation, document) not found

---

## Rate Limiting and Quotas

Rate limits depend on your Dify deployment:
- **Cloud version**: Check your plan limits
- **Self-hosted**: Configure in deployment settings

---

## Best Practices

1. **Always use HTTPS** in production
2. **Handle streaming responses** properly for Agent apps
3. **Implement retry logic** for transient errors
4. **Cache conversation IDs** for multi-turn conversations
5. **Monitor token usage** via metadata in responses
6. **Validate inputs** before sending to API
7. **Set appropriate timeouts** for long-running queries
8. **Use user identifiers** for tracking and analytics

---

## Additional Resources

- Official Documentation: https://docs.dify.ai/
- GitHub Repository: https://github.com/langgenius/dify
- API Specification: Available in Dify documentation
- Community: Dify Discord/Forum

---

*Last Updated: 2024-12-22*
*Source: Dify Official Documentation via Context7*
