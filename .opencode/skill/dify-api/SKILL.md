---
name: dify-api
description: Dify API integration for chat-based LLM applications. Use when integrating with Dify platform, testing Dify endpoints, managing conversations, or working with Dify Agent Chat Apps.
---

# Dify API Integration

Integration skill for Dify API - Open-source LLM application development platform.

## Overview

This skill provides comprehensive tools and documentation for integrating with Dify API. Dify is an open-source platform that combines Backend-as-a-Service and LLMOps to streamline generative AI application development.

**What you can do:**
- Send chat messages to Dify applications
- Manage multi-turn conversations
- Retrieve application parameters and configuration
- Test Dify API endpoints
- Debug Dify integrations

**What's inside:**
```
dify-api/
├── SKILL.md (this file)
├── scripts/
│   ├── test_dify_api.py       # Python script (full API coverage)
│   └── requirements.txt       # Python dependencies
└── references/
    ├── dify-reference.md       # API documentation from Context7
    ├── dify-api-testing.md     # API testing guide (Python)
    ├── dify-app-develop.md     # App API reference (clean English)
    ├── dify-workflow-develop.md # App Workflow API reference
    └── dify-sdk-rs.md          # Dify SDK for Rust (dify-client quick start)
```

## Quick Start

### Python (Full API Coverage)
```bash
# Install dependencies
pip install -r skills/dify-api/scripts/requirements.txt

# Chat
python skills/dify-api/scripts/test_dify_api.py \
  --api-key 'app-xxxxx' \
  --no-proxy \
  chat --query "Hello!"

# App parameters
python skills/dify-api/scripts/test_dify_api.py \
  --api-key 'app-xxxxx' \
  --no-proxy \
  parameters

# Dataset management
python skills/dify-api/scripts/test_dify_api.py \
  --api-key 'app-xxxxx' \
  --no-proxy \
  create-document --dataset-id "xxx" --name "Doc" --text "Content"
```

## Prerequisites

- Python 3.9+
- pip (or uv)
- Dify API key (format: `app-xxxxx`)

## Common Operations Reference

| Operation | Command |
|-----------|---------|
| **Send chat message** | `python .../test_dify_api.py chat --query "hi"` |
| **Get app parameters** | `python .../test_dify_api.py parameters` |
| **List conversations** | `python .../test_dify_api.py conversations --user "test-user"` |
| **Continue conversation** | `python .../test_dify_api.py chat --conversation-id "xxx" --query "follow-up"` |

## Script Parameters

Use `python skills/dify-api/scripts/test_dify_api.py --help` for the full list.

Common flags:

| Flag | Description |
|------|-------------|
| `--api-url` | Dify API base URL |
| `--api-key` | API key (can use `DIFY_API_KEY`) |
| `--no-proxy` | Disable proxy |
| `--skip-cert-check` | Skip SSL verification |

## Known Deployments

### Panasonic Internal
```
https://test-ookoo.is.panasonic.cn/v1
API Key: app-xxxxx (contact admin for actual key)
Model: Qwen
Type: Agent Chat App
Note: Requires -NoProxy flag
```

### Dify Cloud
```
https://api.dify.ai/v1
```

### Local Dev
```
http://localhost/v1
```

## Request/Response Format

### Chat Request
```json
{
    "inputs": {},
    "query": "Your question",
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "user-id"
}
```

### Streaming Response Events
- `agent_message` - Message chunks
- `agent_thought` - Agent reasoning
- `message_end` - Final with usage metadata

### Example Output
```
Streaming Response:
===================
Hello! I'm Qwen...

===================

Usage Information:
  Prompt tokens:     15
  Completion tokens: 42
  Total tokens:      57
  Cost:              0.000095 RMB
  Latency:           2.134s
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| Connection reset | Add `--no-proxy` |
| SSL failed | Add `--skip-cert-check` |
| Unauthorized | Check API key format (app-xxx) |
| "Blocking mode not supported" | Automatic (uses streaming) |

**Debug tips:**
1. Test connectivity: `python .../test_dify_api.py parameters`
2. Check streaming output in console
3. Verify API key starts with `app-`
4. Monitor token usage in response
5. Script shows request details automatically

## Differences from OpenAI API

| Feature | OpenAI | Dify |
|---------|--------|------|
| Endpoint | `/v1/chat/completions` | `/v1/chat-messages` |
| Request | `messages` array | `query` + `inputs` |
| Response mode | `stream` boolean | `response_mode` string |
| Model | `model` parameter | Pre-configured in app |
| Auth | `Bearer sk-...` | `Bearer app-...` |

## Integration Checklist

- [ ] API key obtained from Dify app
- [ ] Base URL configured
- [ ] Python installed
- [ ] Network access verified
- [ ] Proxy settings configured (`--no-proxy` if needed)

## Use Cases

1. Testing Dify Applications
2. Multi-turn Conversation Testing
3. Integration Development
4. Debugging Dify Issues
5. Automation & Batch Processing
6. Multi-environment Testing

## Key Features

### Python Script (test_dify_api.py) - Full Coverage
✅ Message feedback (like/dislike)
✅ Stop message generation
✅ App info/meta/site
✅ Conversations (list/delete/rename)
✅ Conversation variables (list/update)
✅ Audio-to-text and text-to-audio
✅ Dataset document creation
✅ Metadata field management (add/update/delete/list)
✅ Built-in metadata toggle
✅ Better error handling
✅ Retry logic
✅ Cross-platform support

## Documentation

- **[dify-reference.md](references/dify-reference.md)** - Detailed API docs from Context7
- **[dify-api-testing.md](references/dify-api-testing.md)** - Python API testing guide
- **[dify-app-develop.md](references/dify-app-develop.md)** - App chat-messages API reference
- **[dify-workflow-develop.md](references/dify-workflow-develop.md)** - App Workflow API reference
- **[dify-sdk-rs.md](references/dify-sdk-rs.md)** - Dify SDK for Rust (dify-client) quick start guide
## Related Skills

- `rig-integration` - OpenAI-compatible API integration
