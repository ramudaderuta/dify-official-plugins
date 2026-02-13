# Dify API Testing Guide

Practical guide for testing Dify API endpoints with the bundled Python client.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Python Examples](#python-examples)
- [Complete Workflows](#complete-workflows)
- [Command Reference](#command-reference)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Python Client (Recommended)

```bash
# Install dependencies
pip install -r skills/dify-api/scripts/requirements.txt

# Or use uv
uv pip install -r skills/dify-api/scripts/requirements.txt
```

## Quick Start

### Environment Setup

```bash
# Linux/Mac
export DIFY_API_KEY="app-your-api-key"
export DIFY_API_URL="https://test-ookoo.is.panasonic.cn/v1"

# Windows PowerShell
$env:DIFY_API_KEY = "app-your-api-key"
$env:DIFY_API_URL = "https://test-ookoo.is.panasonic.cn/v1"

# Windows CMD
set DIFY_API_KEY=app-your-api-key
set DIFY_API_URL=https://test-ookoo.is.panasonic.cn/v1
```

### Basic Chat (Python)

```bash
python skills/dify-api/scripts/test_dify_api.py \
  --api-key 'app-xxxxx' \
  --no-proxy \
  chat --query "Hello!"
```

---

## Python Examples

### Chat Commands

#### Basic Chat
```bash
python test_dify_api.py chat --query "Hello, how are you?"
```

**Output:**
```
🔵 Request: POST https://test-ookoo.is.panasonic.cn/v1/chat-messages
📤 Body: {"inputs": {}, "query": "Hello", ...}

==================================================
📨 Streaming Response:
==================================================

Hello! I'm Qwen, a large-scale language model...

==================================================

📊 Usage Information:
  Prompt tokens:     15
  Completion tokens: 42
  Total tokens:      57
  Cost:              0.000095 RMB
  Latency:           2.134s

✅ Command completed successfully!
```

#### Chat with Custom Inputs
```bash
python test_dify_api.py chat \
  --query "Translate this text" \
  --inputs '{"language":"zh","style":"formal"}'
```

#### Continue Conversation
```bash
# First message
python test_dify_api.py chat --query "Tell me about AI" --no-proxy

# Follow-up (use conversation_id from response)
python test_dify_api.py chat \
  --query "Tell me more" \
  --conversation-id "xxx-xxx-xxx" \
  --no-proxy
```

#### Custom User ID
```bash
python test_dify_api.py chat \
  --query "Hello" \
  --user "user-12345" \
  --no-proxy
```

### Application Info Commands

#### Get App Parameters
```bash
python test_dify_api.py parameters --no-proxy
```

#### Get Conversation List
```bash
python test_dify_api.py conversations --no-proxy
```

### Message Control Commands

#### Stop Message Generation
```bash
python test_dify_api.py stop --task-id "task-xxx-xxx" --no-proxy
```

#### Provide Feedback
```bash
# Like a message
python test_dify_api.py feedback \
  --message-id "msg-xxx-xxx" \
  --rating like \
  --no-proxy

# Dislike a message
python test_dify_api.py feedback \
  --message-id "msg-xxx-xxx" \
  --rating dislike \
  --no-proxy
```

### Dataset Management Commands

#### Create Document from Text
```bash
python test_dify_api.py create-document \
  --dataset-id "dataset-xxx" \
  --name "Product Manual" \
  --text "This is the product manual content..." \
  --no-proxy
```

#### Create Document with Custom Indexing
```bash
python test_dify_api.py create-document \
  --dataset-id "dataset-xxx" \
  --name "FAQ Document" \
  --text "Q: How to install? A: Follow these steps..." \
  --indexing "high_quality" \
  --process-mode "automatic" \
  --no-proxy
```

#### Add Metadata Field
```bash
# Add string field
python test_dify_api.py add-metadata \
  --dataset-id "dataset-xxx" \
  --field-type string \
  --name "author" \
  --no-proxy

# Add number field
python test_dify_api.py add-metadata \
  --dataset-id "dataset-xxx" \
  --field-type number \
  --name "version" \
  --no-proxy

# Add time field
python test_dify_api.py add-metadata \
  --dataset-id "dataset-xxx" \
  --field-type time \
  --name "published_date" \
  --no-proxy
```

#### Update Metadata Field
```bash
python test_dify_api.py update-metadata \
  --dataset-id "dataset-xxx" \
  --metadata-id "meta-xxx" \
  --name "new_field_name" \
  --no-proxy
```

#### Delete Metadata Field
```bash
python test_dify_api.py delete-metadata \
  --dataset-id "dataset-xxx" \
  --metadata-id "meta-xxx" \
  --no-proxy
```

#### List Metadata Fields
```bash
python test_dify_api.py list-metadata \
  --dataset-id "dataset-xxx" \
  --no-proxy
```

#### Enable/Disable Built-in Metadata
```bash
# Enable built-in metadata
python test_dify_api.py toggle-builtin-metadata \
  --dataset-id "dataset-xxx" \
  --action enable \
  --no-proxy

# Disable built-in metadata
python test_dify_api.py toggle-builtin-metadata \
  --dataset-id "dataset-xxx" \
  --action disable \
  --no-proxy
```

---

## Complete Workflows

### Chat Workflow (Python)

```bash
# 1. Check app parameters
python test_dify_api.py parameters --no-proxy

# 2. Start a conversation
python test_dify_api.py chat \
  --query "What is machine learning?" \
  --no-proxy

# 3. Continue the conversation (use conversation_id from step 2)
python test_dify_api.py chat \
  --query "Can you give me an example?" \
  --conversation-id "conv-xxx-xxx" \
  --no-proxy

# 4. List all conversations
python test_dify_api.py conversations --no-proxy

# 5. Provide feedback
python test_dify_api.py feedback \
  --message-id "msg-xxx-xxx" \
  --rating like \
  --no-proxy
```

### Dataset Management Workflow (Python)

```bash
# 1. Create a new document
python test_dify_api.py create-document \
  --dataset-id "dataset-xxx" \
  --name "Product Guide" \
  --text "Complete product installation and usage guide..." \
  --no-proxy

# 2. Add metadata fields
python test_dify_api.py add-metadata \
  --dataset-id "dataset-xxx" \
  --field-type string \
  --name "category" \
  --no-proxy

python test_dify_api.py add-metadata \
  --dataset-id "dataset-xxx" \
  --field-type time \
  --name "last_updated" \
  --no-proxy

# 3. List all metadata fields
python test_dify_api.py list-metadata \
  --dataset-id "dataset-xxx" \
  --no-proxy

# 4. Update a metadata field
python test_dify_api.py update-metadata \
  --dataset-id "dataset-xxx" \
  --metadata-id "meta-xxx" \
  --name "product_category" \
  --no-proxy
```

---

## Command Reference

### Python Commands

| Command | Description | Key Options |
|---------|-------------|-------------|
| `chat` | Send chat message | `--query`, `--conversation-id`, `--inputs`, `--user`, `--response-mode`, `--files` |
| `parameters` | Get app parameters | - |
| `info` | Get app info | - |
| `meta` | Get app meta | - |
| `site` | Get app site settings | - |
| `conversations` | List conversations | `--user`, `--last-id`, `--limit`, `--sort-by` |
| `delete-conversation` | Delete conversation | `--conversation-id`, `--user` |
| `rename-conversation` | Rename conversation | `--conversation-id`, `--user`, `--name`, `--auto-generate` |
| `variables` | List conversation variables | `--conversation-id`, `--user`, `--limit`, `--variable-name` |
| `update-variable` | Update conversation variable | `--conversation-id`, `--variable-id`, `--user`, `--value` |
| `stop` | Stop message generation | `--task-id`, `--user` |
| `feedback` | Provide feedback | `--message-id`, `--rating` (`like`/`dislike`) |
| `audio-to-text` | Speech to text | `--file`, `--user` |
| `text-to-audio` | Text to speech | `--message-id`/`--text`, `--user`, `--output` |
| `create-document` | Create document | `--dataset-id`, `--name`, `--text`, `--indexing`, `--process-mode` |
| `add-metadata` | Add metadata field | `--dataset-id`, `--field-type` (`string`/`number`/`time`), `--name` |
| `update-metadata` | Update metadata field | `--dataset-id`, `--metadata-id`, `--name` |
| `delete-metadata` | Delete metadata field | `--dataset-id`, `--metadata-id` |
| `list-metadata` | List metadata fields | `--dataset-id` |
| `toggle-builtin-metadata` | Toggle built-in metadata | `--dataset-id`, `--action` (`enable`/`disable`) |

### Global Options (Python)

| Option | Description |
|--------|-------------|
| `--api-url` | Override API base URL |
| `--api-key` | Override API key |
| `--no-proxy` | Disable proxy (recommended for Panasonic internal) |
| `--skip-cert-check` | Skip SSL certificate verification |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DIFY_API_KEY` | Dify API key | Required |
| `DIFY_API_URL` | Dify API base URL | `https://test-ookoo.is.panasonic.cn/v1` |

---

## Network Options

### Use Direct Connection (No Proxy)

**Python:**
```bash
python test_dify_api.py chat --query "Hello" --no-proxy
```

### Skip SSL Certificate Verification

**Python:**
```bash
python test_dify_api.py chat --query "Hello" --skip-cert-check
```

### Custom API URL

**Python:**
```bash
python test_dify_api.py chat \
  --query "Hello" \
  --api-url "https://your-dify-instance.com/v1"
```

---

## Troubleshooting

### Connection Issues

**Problem: Connection reset**

**Solution (Python):**
```bash
python test_dify_api.py chat --query "Hello" --no-proxy
```

**Problem: SSL certificate error**

**Solution (Python):**
```bash
python test_dify_api.py chat --query "Hello" --skip-cert-check
```

### API Key Issues

**Check if API key is set:**

```bash
# Linux/Mac
echo $DIFY_API_KEY

# Windows CMD
echo %DIFY_API_KEY%

# Windows PowerShell
echo $env:DIFY_API_KEY
```

**Error: Invalid API key**
- Ensure key starts with `app-`
- Verify key hasn't expired
- Check key permissions in Dify app

### Python Import Errors

```bash
# Install missing dependencies
pip install requests urllib3

# Or reinstall all requirements
pip install -r skills/dify-api/scripts/requirements.txt
```

---

## Tips & Best Practices

1. **For Panasonic Internal Network**: Always use `--no-proxy`
2. **Environment Variables**: Set `DIFY_API_KEY` and `DIFY_API_URL` to avoid repetitive typing
3. **JSON Inputs**: Use single quotes for JSON strings: `--inputs '{"key":"value"}'`
4. **Conversation ID**: Save the conversation_id from the first chat to continue conversations
5. **Error Details**: Scripts show detailed error messages including API responses
6. **Rate Limiting**: Add delays between batch requests to avoid rate limits
7. **User IDs**: Use meaningful user identifiers for tracking and analytics

---

## Error Messages Reference

| Error | Meaning | Solution |
|-------|---------|----------|
| "Connection reset" | Network/proxy issue | Add `--no-proxy` or `-NoProxy` |
| "SSL connection failed" | Certificate issue | Add `--skip-cert-check` or `-SkipCertCheck` |
| "Unauthorized" | Invalid API key | Check key format (app-xxx) |
| "Agent Chat App does not support blocking mode" | App requires streaming | Automatic (uses streaming) |
| "HTTP 404" | Endpoint not found | Check API URL and endpoint path |
| "HTTP 429" | Rate limit exceeded | Add delays between requests |

---

*Last Updated: 2024-12-22*

