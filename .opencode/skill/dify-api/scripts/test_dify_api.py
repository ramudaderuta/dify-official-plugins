#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dify API testing script with comprehensive endpoint coverage.

Usage:
    python test_dify_api.py --help
    python test_dify_api.py chat --query "Hello"
    python test_dify_api.py parameters
    python test_dify_api.py conversations
"""

import argparse
import json
import os
import sys
from typing import Optional, Dict, Any, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set UTF-8 encoding for Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class DifyAPIClient:
    """Client for interacting with Dify API."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        no_proxy: bool = False,
        skip_cert_check: bool = False,
        timeout: int = 60
    ):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Configure headers
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })

        # Configure proxy
        if no_proxy:
            self.session.trust_env = False
            self.session.proxies = {'http': None, 'https': None}

        # Configure SSL verification
        self.verify = not skip_cert_check
        if skip_cert_check:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            print("⚠️  WARNING: SSL certificate validation is disabled")

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Dify API."""
        url = f"{self.api_url}/{endpoint}"
        print(f"\n🔵 Request: {method.upper()} {url}")

        if 'json' in kwargs:
            print(f"📤 Body: {json.dumps(kwargs['json'], ensure_ascii=False)}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                verify=self.verify,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"📥 Error Details: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"📥 Response: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            raise

    def _multipart_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """Make multipart/form-data request to Dify API."""
        url = f"{self.api_url}/{endpoint}"
        print(f"\n🔵 Request: {method.upper()} {url}")
        if data:
            print(f"📤 Form: {json.dumps(data, ensure_ascii=False)}")
        if files:
            print(f"📎 Files: {', '.join(files.keys())}")

        headers = dict(self.session.headers)
        headers.pop('Content-Type', None)

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                files=files,
                verify=self.verify,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"📥 Error Details: {json.dumps(error_detail, indent=2)}")
                except:
                    print(f"📥 Response: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            raise

    def _stream_request(self, endpoint: str, data: Dict[str, Any]):
        """Make streaming request to Dify API."""
        url = f"{self.api_url}/{endpoint}"
        print(f"\n🔵 Request: POST {url}")
        print(f"📤 Body: {json.dumps(data, ensure_ascii=False)}")

        try:
            response = self.session.post(
                url,
                json=data,
                stream=True,
                verify=self.verify,
                timeout=self.timeout
            )
            response.raise_for_status()

            print("\n" + "="*50)
            print("📨 Streaming Response:")
            print("="*50 + "\n")

            full_answer = ""
            metadata = None

            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith('data: '):
                    continue

                try:
                    data_str = line[6:]  # Remove 'data: ' prefix
                    event_data = json.loads(data_str)
                    event_type = event_data.get('event')

                    if event_type in ('message', 'agent_message'):
                        answer = event_data.get('answer', '')
                        if answer:
                            print(answer, end='', flush=True)
                            full_answer += answer

                    elif event_type == 'agent_thought':
                        thought = event_data.get('thought', '')
                        if thought and thought.strip():
                            print(f"\n\n💭 [Agent Thought]\n{thought}")
                        tool = event_data.get('tool')
                        observation = event_data.get('observation')
                        if tool or observation:
                            print(f"\n🛠️  Tool: {tool or ''}\n📥 Observation: {observation or ''}")

                    elif event_type == 'message_file':
                        file_url = event_data.get('url')
                        file_type = event_data.get('type')
                        print(f"\n\n📎 [Message File] type={file_type} url={file_url}")

                    elif event_type == 'message_replace':
                        replacement = event_data.get('answer', '')
                        if replacement:
                            print(f"\n\n🔁 [Message Replace]\n{replacement}")

                    elif event_type == 'message_end':
                        metadata = event_data.get('metadata')

                    elif event_type == 'error':
                        status = event_data.get('status')
                        code = event_data.get('code')
                        message = event_data.get('message')
                        print(f"\n\n❌ [Stream Error] status={status} code={code} message={message}")
                        break

                except json.JSONDecodeError:
                    continue

            print("\n\n" + "="*50)

            if metadata and metadata.get('usage'):
                usage = metadata['usage']
                print("\n📊 Usage Information:")
                print(f"  Prompt tokens:     {usage.get('prompt_tokens', 'N/A')}")
                print(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}")
                print(f"  Total tokens:      {usage.get('total_tokens', 'N/A')}")
                print(f"  Cost:              {usage.get('total_price', 'N/A')} {usage.get('currency', 'RMB')}")
                if 'latency' in usage:
                    print(f"  Latency:           {usage['latency']:.3f}s")

            return {
                'answer': full_answer,
                'metadata': metadata
            }

        except requests.exceptions.RequestException as e:
            print(f"❌ Streaming request failed: {e}")
            raise

    # ==================== Chat APIs ====================

    def chat(
        self,
        query: str,
        user: str = "test-user",
        conversation_id: str = "",
        inputs: Optional[Dict[str, Any]] = None,
        response_mode: str = "streaming",
        files: Optional[List[Dict[str, Any]]] = None,
        auto_generate_name: Optional[bool] = None,
        workflow_id: str = "",
        trace_id: str = ""
    ) -> Dict[str, Any]:
        """Send chat message."""
        data = {
            "inputs": inputs or {},
            "query": query,
            "response_mode": response_mode,
            "user": user
        }

        if conversation_id:
            data["conversation_id"] = conversation_id
            print(f"📝 Continuing conversation: {conversation_id}")

        if files:
            if not isinstance(files, list):
                raise ValueError("--files must be a JSON array of file objects")
            data["files"] = files
            print("🧪 Note: files is a test-only JSON input for API coverage.")

        if auto_generate_name is not None:
            data["auto_generate_name"] = auto_generate_name

        if workflow_id:
            data["workflow_id"] = workflow_id

        if trace_id:
            data["trace_id"] = trace_id

        if response_mode == "blocking":
            result = self._request('POST', 'chat-messages', json=data)
            print("\n✅ Response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result

        return self._stream_request("chat-messages", data)

    def get_parameters(self) -> Dict[str, Any]:
        """Get application parameters."""
        print("🔍 Getting app parameters...")
        result = self._request('GET', 'parameters')
        print("\n✅ App Parameters:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def get_conversations(
        self,
        user: str,
        last_id: str = "",
        limit: Optional[int] = None,
        sort_by: str = ""
    ) -> Dict[str, Any]:
        """Get conversation list."""
        print("🔍 Getting conversation list...")
        params: Dict[str, Any] = {"user": user}
        if last_id:
            params["last_id"] = last_id
        if limit is not None:
            params["limit"] = limit
        if sort_by:
            params["sort_by"] = sort_by
        result = self._request('GET', 'conversations', params=params)

        if result.get('data'):
            print(f"\n📋 Conversations:")
            for conv in result['data']:
                print(f"\n  ID: {conv.get('id')}")
                print(f"  Created: {conv.get('created_at')}")
                print(f"  Status: {conv.get('status')}")
                if conv.get('summary'):
                    print(f"  Summary: {conv.get('summary')}")
            print(f"\n✅ Total: {len(result['data'])} conversations")
        else:
            print("\n⚠️  No conversations found.")

        return result

    def delete_conversation(self, conversation_id: str, user: str) -> Dict[str, Any]:
        """Delete conversation."""
        print(f"🗑️  Deleting conversation: {conversation_id}")
        data = {"user": user}
        result = self._request('DELETE', f'conversations/{conversation_id}', json=data)
        print("✅ Conversation deleted")
        return result

    def rename_conversation(
        self,
        conversation_id: str,
        user: str,
        name: str = "",
        auto_generate: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Rename conversation."""
        print(f"✏️  Renaming conversation: {conversation_id}")
        data: Dict[str, Any] = {"user": user}
        if name:
            data["name"] = name
        if auto_generate is not None:
            data["auto_generate"] = auto_generate
        result = self._request('POST', f'conversations/{conversation_id}/name', json=data)
        print("✅ Conversation renamed")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def get_conversation_variables(
        self,
        conversation_id: str,
        user: str,
        last_id: str = "",
        limit: Optional[int] = None,
        variable_name: str = ""
    ) -> Dict[str, Any]:
        """Get conversation variables."""
        print(f"🔍 Getting variables for conversation: {conversation_id}")
        params: Dict[str, Any] = {"user": user}
        if last_id:
            params["last_id"] = last_id
        if limit is not None:
            params["limit"] = limit
        if variable_name:
            params["variable_name"] = variable_name
        result = self._request('GET', f'conversations/{conversation_id}/variables', params=params)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def update_conversation_variable(
        self,
        conversation_id: str,
        variable_id: str,
        user: str,
        value: Any
    ) -> Dict[str, Any]:
        """Update conversation variable."""
        print(f"✏️  Updating variable: {variable_id}")
        data = {"value": value, "user": user}
        result = self._request('PUT', f'conversations/{conversation_id}/variables/{variable_id}', json=data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def get_info(self) -> Dict[str, Any]:
        """Get app info."""
        print("🔍 Getting app info...")
        result = self._request('GET', 'info')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def get_meta(self) -> Dict[str, Any]:
        """Get app meta info."""
        print("🔍 Getting app meta...")
        result = self._request('GET', 'meta')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def get_site(self) -> Dict[str, Any]:
        """Get app site settings."""
        print("🔍 Getting app site settings...")
        result = self._request('GET', 'site')
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def audio_to_text(self, file_path: str, user: str) -> Dict[str, Any]:
        """Speech to text."""
        print(f"🎙️  Converting audio to text: {file_path}")
        with open(file_path, 'rb') as f:
            files = {"file": (os.path.basename(file_path), f)}
            data = {"user": user}
            response = self._multipart_request('POST', 'audio-to-text', data=data, files=files)
            result = response.json() if response.text else {}
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return result

    def text_to_audio(
        self,
        user: str,
        message_id: str = "",
        text: str = "",
        output: str = ""
    ) -> Dict[str, Any]:
        """Text to speech."""
        print("🔊 Converting text to audio...")
        data: Dict[str, Any] = {"user": user}
        if message_id:
            data["message_id"] = message_id
        if text:
            data["text"] = text

        response = self._multipart_request('POST', 'text-to-audio', data=data)
        content_type = response.headers.get('Content-Type', '')
        if output:
            with open(output, 'wb') as f:
                f.write(response.content)
            print(f"✅ Audio saved: {output} ({content_type}, {len(response.content)} bytes)")
            return {"output": output, "content_type": content_type, "bytes": len(response.content)}

        print(f"✅ Audio received: {content_type}, {len(response.content)} bytes")
        return {"content_type": content_type, "bytes": len(response.content)}

    def stop_message(self, task_id: str, user: str = "test-user") -> Dict[str, Any]:
        """Stop message generation."""
        print(f"🛑 Stopping message generation for task: {task_id}")
        data = {
            "task_id": task_id,
            "user": user
        }
        result = self._request('POST', 'chat-messages/stop', json=data)
        print("✅ Message generation stopped")
        return result

    def message_feedback(
        self,
        message_id: str,
        rating: str,
        user: str = "test-user"
    ) -> Dict[str, Any]:
        """Provide feedback for a message."""
        print(f"⭐ Providing feedback for message: {message_id}")
        data = {
            "message_id": message_id,
            "rating": rating,  # 'like' or 'dislike'
            "user": user
        }
        result = self._request('POST', 'messages/feedback', json=data)
        print(f"✅ Feedback submitted: {rating}")
        return result

    # ==================== Dataset APIs ====================

    def create_document_by_text(
        self,
        dataset_id: str,
        name: str,
        text: str,
        indexing_technique: str = "high_quality",
        process_mode: str = "automatic"
    ) -> Dict[str, Any]:
        """Create knowledge base document from text."""
        print(f"📄 Creating document in dataset: {dataset_id}")
        data = {
            "name": name,
            "text": text,
            "indexing_technique": indexing_technique,
            "process_rule": {
                "mode": process_mode
            }
        }
        result = self._request(
            'POST',
            f'datasets/{dataset_id}/document/create_by_text',
            json=data
        )
        print(f"✅ Document created: {result.get('document', {}).get('id')}")
        return result

    def add_metadata_field(
        self,
        dataset_id: str,
        field_type: str,
        name: str
    ) -> Dict[str, Any]:
        """Add metadata field to dataset."""
        print(f"➕ Adding metadata field '{name}' to dataset: {dataset_id}")
        data = {
            "type": field_type,  # 'string', 'number', 'time'
            "name": name
        }
        result = self._request(
            'POST',
            f'datasets/{dataset_id}/metadata',
            json=data
        )
        print(f"✅ Metadata field added: {result.get('id')}")
        return result

    def update_metadata_field(
        self,
        dataset_id: str,
        metadata_id: str,
        name: str
    ) -> Dict[str, Any]:
        """Update metadata field in dataset."""
        print(f"✏️  Updating metadata field: {metadata_id}")
        data = {"name": name}
        result = self._request(
            'PATCH',
            f'datasets/{dataset_id}/metadata/{metadata_id}',
            json=data
        )
        print(f"✅ Metadata field updated")
        return result

    def delete_metadata_field(
        self,
        dataset_id: str,
        metadata_id: str
    ) -> Dict[str, Any]:
        """Delete metadata field from dataset."""
        print(f"🗑️  Deleting metadata field: {metadata_id}")
        result = self._request(
            'DELETE',
            f'datasets/{dataset_id}/metadata/{metadata_id}'
        )
        print(f"✅ Metadata field deleted")
        return result

    def get_metadata_list(self, dataset_id: str) -> Dict[str, Any]:
        """Get dataset metadata list."""
        print(f"🔍 Getting metadata list for dataset: {dataset_id}")
        result = self._request('GET', f'datasets/{dataset_id}/metadata')

        if result.get('doc_metadata'):
            print(f"\n📋 Metadata Fields:")
            for field in result['doc_metadata']:
                print(f"\n  ID: {field.get('id')}")
                print(f"  Type: {field.get('type')}")
                print(f"  Name: {field.get('name')}")
                print(f"  Use count: {field.get('use_count', 0)}")
            print(f"\n✅ Total fields: {len(result['doc_metadata'])}")

        return result

    def toggle_builtin_metadata(
        self,
        dataset_id: str,
        action: str  # 'enable' or 'disable'
    ) -> Dict[str, Any]:
        """Enable or disable built-in metadata fields."""
        print(f"🔧 {action.capitalize()}ing built-in metadata fields")
        result = self._request(
            'DELETE',
            f'datasets/{dataset_id}/metadata/built-in/{action}'
        )
        print(f"✅ Built-in metadata fields {action}d")
        return result


def main():
    def parse_json_arg(value: str) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise argparse.ArgumentTypeError(f"Invalid JSON: {exc.msg}") from exc

    parser = argparse.ArgumentParser(
        description='Dify API Testing Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Chat
  python test_dify_api.py chat --query "Hello, how are you?"
  python test_dify_api.py chat --query "Continue" --conversation-id "xxx-xxx-xxx"
  python test_dify_api.py chat --query "Hello" --response-mode blocking
  python test_dify_api.py chat --query "Hello" --files '[{\"type\":\"image\",\"transfer_method\":\"remote_url\",\"url\":\"https://example.com/a.png\"}]'

  # App info
  python test_dify_api.py info
  python test_dify_api.py meta
  python test_dify_api.py site
  python test_dify_api.py parameters
  python test_dify_api.py conversations --user "test-user"

  # Dataset management
  python test_dify_api.py create-document --dataset-id "xxx" --name "Test" --text "Content"
  python test_dify_api.py add-metadata --dataset-id "xxx" --field-type string --name "author"
  python test_dify_api.py list-metadata --dataset-id "xxx"

  # Conversation management
  python test_dify_api.py delete-conversation --conversation-id "xxx" --user "test-user"
  python test_dify_api.py rename-conversation --conversation-id "xxx" --user "test-user" --name "New Title"
  python test_dify_api.py variables --conversation-id "xxx" --user "test-user"
  python test_dify_api.py update-variable --conversation-id "xxx" --variable-id "var-xxx" --user "test-user" --value '\"new\"'

  # Audio
  python test_dify_api.py audio-to-text --file "sample.wav" --user "test-user"
  python test_dify_api.py text-to-audio --text "Hello" --user "test-user" --output "out.wav"
        """
    )

    # Global arguments
    parser.add_argument(
        '--api-url',
        default=os.getenv('DIFY_API_URL', 'https://test-ookoo.is.panasonic.cn/v1'),
        help='Dify API base URL'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('DIFY_API_KEY'),
        help='Dify API key'
    )
    parser.add_argument(
        '--no-proxy',
        action='store_true',
        help='Disable proxy'
    )
    parser.add_argument(
        '--skip-cert-check',
        action='store_true',
        help='Skip SSL certificate verification'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Send chat message')
    chat_parser.add_argument('--query', required=True, help='User query')
    chat_parser.add_argument('--user', default='test-user', help='User identifier')
    chat_parser.add_argument('--conversation-id', default='', help='Conversation ID')
    chat_parser.add_argument('--inputs', type=parse_json_arg, default={}, help='Additional inputs as JSON')
    chat_parser.add_argument('--response-mode', choices=['streaming', 'blocking'], default='streaming', help='Response mode')
    chat_parser.add_argument('--files', type=parse_json_arg, default=None, help='Files JSON (testing only)')
    auto_name_group = chat_parser.add_mutually_exclusive_group()
    auto_name_group.add_argument('--auto-generate-name', dest='auto_generate_name', action='store_true', help='Auto-generate title')
    auto_name_group.add_argument('--no-auto-generate-name', dest='auto_generate_name', action='store_false', help='Disable auto title')
    chat_parser.set_defaults(auto_generate_name=None)
    chat_parser.add_argument('--workflow-id', default='', help='Workflow version ID')
    chat_parser.add_argument('--trace-id', default='', help='Trace ID (testing)')

    # Parameters command
    subparsers.add_parser('parameters', help='Get app parameters')

    # App info commands
    subparsers.add_parser('info', help='Get app info')
    subparsers.add_parser('meta', help='Get app meta')
    subparsers.add_parser('site', help='Get app site settings')

    # Conversations command
    conv_parser = subparsers.add_parser('conversations', help='Get conversation list')
    conv_parser.add_argument('--user', default='test-user', help='User identifier')
    conv_parser.add_argument('--last-id', default='', help='Paging cursor')
    conv_parser.add_argument('--limit', type=int, default=None, help='Page size (1-100)')
    conv_parser.add_argument('--sort-by', default='', help='Sort field (e.g., -updated_at)')

    delete_conv_parser = subparsers.add_parser('delete-conversation', help='Delete conversation')
    delete_conv_parser.add_argument('--conversation-id', required=True, help='Conversation ID')
    delete_conv_parser.add_argument('--user', default='test-user', help='User identifier')

    rename_conv_parser = subparsers.add_parser('rename-conversation', help='Rename conversation')
    rename_conv_parser.add_argument('--conversation-id', required=True, help='Conversation ID')
    rename_conv_parser.add_argument('--user', default='test-user', help='User identifier')
    rename_conv_parser.add_argument('--name', default='', help='New name')
    rename_auto_group = rename_conv_parser.add_mutually_exclusive_group()
    rename_auto_group.add_argument('--auto-generate', dest='auto_generate', action='store_true', help='Auto-generate name')
    rename_auto_group.add_argument('--no-auto-generate', dest='auto_generate', action='store_false', help='Disable auto-generate')
    rename_conv_parser.set_defaults(auto_generate=None)

    vars_parser = subparsers.add_parser('variables', help='Get conversation variables')
    vars_parser.add_argument('--conversation-id', required=True, help='Conversation ID')
    vars_parser.add_argument('--user', default='test-user', help='User identifier')
    vars_parser.add_argument('--last-id', default='', help='Paging cursor')
    vars_parser.add_argument('--limit', type=int, default=None, help='Page size (1-100)')
    vars_parser.add_argument('--variable-name', default='', help='Filter by variable name')

    update_var_parser = subparsers.add_parser('update-variable', help='Update conversation variable')
    update_var_parser.add_argument('--conversation-id', required=True, help='Conversation ID')
    update_var_parser.add_argument('--variable-id', required=True, help='Variable ID')
    update_var_parser.add_argument('--user', default='test-user', help='User identifier')
    update_var_parser.add_argument('--value', required=True, type=parse_json_arg, help='New value as JSON')

    audio_to_text_parser = subparsers.add_parser('audio-to-text', help='Speech to text')
    audio_to_text_parser.add_argument('--file', required=True, help='Audio file path')
    audio_to_text_parser.add_argument('--user', default='test-user', help='User identifier')

    text_to_audio_parser = subparsers.add_parser('text-to-audio', help='Text to speech')
    text_to_audio_parser.add_argument('--message-id', default='', help='Message ID')
    text_to_audio_parser.add_argument('--text', default='', help='Text content')
    text_to_audio_parser.add_argument('--user', default='test-user', help='User identifier')
    text_to_audio_parser.add_argument('--output', default='', help='Output audio file path')

    # Stop message command
    stop_parser = subparsers.add_parser('stop', help='Stop message generation')
    stop_parser.add_argument('--task-id', required=True, help='Task ID')
    stop_parser.add_argument('--user', default='test-user', help='User identifier')

    # Feedback command
    feedback_parser = subparsers.add_parser('feedback', help='Provide message feedback')
    feedback_parser.add_argument('--message-id', required=True, help='Message ID')
    feedback_parser.add_argument('--rating', required=True, choices=['like', 'dislike'], help='Rating')
    feedback_parser.add_argument('--user', default='test-user', help='User identifier')

    # Create document command
    doc_parser = subparsers.add_parser('create-document', help='Create document from text')
    doc_parser.add_argument('--dataset-id', required=True, help='Dataset ID')
    doc_parser.add_argument('--name', required=True, help='Document name')
    doc_parser.add_argument('--text', required=True, help='Document text content')
    doc_parser.add_argument('--indexing', default='high_quality', help='Indexing technique')
    doc_parser.add_argument('--process-mode', default='automatic', help='Process mode')

    # Add metadata field command
    add_meta_parser = subparsers.add_parser('add-metadata', help='Add metadata field')
    add_meta_parser.add_argument('--dataset-id', required=True, help='Dataset ID')
    add_meta_parser.add_argument('--field-type', required=True, choices=['string', 'number', 'time'], help='Field type')
    add_meta_parser.add_argument('--name', required=True, help='Field name')

    # Update metadata field command
    update_meta_parser = subparsers.add_parser('update-metadata', help='Update metadata field')
    update_meta_parser.add_argument('--dataset-id', required=True, help='Dataset ID')
    update_meta_parser.add_argument('--metadata-id', required=True, help='Metadata field ID')
    update_meta_parser.add_argument('--name', required=True, help='New field name')

    # Delete metadata field command
    del_meta_parser = subparsers.add_parser('delete-metadata', help='Delete metadata field')
    del_meta_parser.add_argument('--dataset-id', required=True, help='Dataset ID')
    del_meta_parser.add_argument('--metadata-id', required=True, help='Metadata field ID')

    # List metadata command
    list_meta_parser = subparsers.add_parser('list-metadata', help='List metadata fields')
    list_meta_parser.add_argument('--dataset-id', required=True, help='Dataset ID')

    # Toggle built-in metadata command
    toggle_meta_parser = subparsers.add_parser('toggle-builtin-metadata', help='Enable/disable built-in metadata')
    toggle_meta_parser.add_argument('--dataset-id', required=True, help='Dataset ID')
    toggle_meta_parser.add_argument('--action', required=True, choices=['enable', 'disable'], help='Action')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not args.api_key:
        print("❌ Error: API key required. Set DIFY_API_KEY environment variable or use --api-key")
        sys.exit(1)

    # Create client
    client = DifyAPIClient(
        api_url=args.api_url,
        api_key=args.api_key,
        no_proxy=args.no_proxy,
        skip_cert_check=args.skip_cert_check
    )

    try:
        # Execute command
        if args.command == 'chat':
            client.chat(
                query=args.query,
                user=args.user,
                conversation_id=args.conversation_id,
                inputs=args.inputs,
                response_mode=args.response_mode,
                files=args.files,
                auto_generate_name=args.auto_generate_name,
                workflow_id=args.workflow_id,
                trace_id=args.trace_id
            )

        elif args.command == 'parameters':
            client.get_parameters()

        elif args.command == 'info':
            client.get_info()

        elif args.command == 'meta':
            client.get_meta()

        elif args.command == 'site':
            client.get_site()

        elif args.command == 'conversations':
            client.get_conversations(
                user=args.user,
                last_id=args.last_id,
                limit=args.limit,
                sort_by=args.sort_by
            )

        elif args.command == 'delete-conversation':
            client.delete_conversation(conversation_id=args.conversation_id, user=args.user)

        elif args.command == 'rename-conversation':
            client.rename_conversation(
                conversation_id=args.conversation_id,
                user=args.user,
                name=args.name,
                auto_generate=args.auto_generate
            )

        elif args.command == 'variables':
            client.get_conversation_variables(
                conversation_id=args.conversation_id,
                user=args.user,
                last_id=args.last_id,
                limit=args.limit,
                variable_name=args.variable_name
            )

        elif args.command == 'update-variable':
            client.update_conversation_variable(
                conversation_id=args.conversation_id,
                variable_id=args.variable_id,
                user=args.user,
                value=args.value
            )

        elif args.command == 'audio-to-text':
            client.audio_to_text(file_path=args.file, user=args.user)

        elif args.command == 'text-to-audio':
            if not args.message_id and not args.text:
                print("❌ Error: provide --message-id or --text for text-to-audio")
                sys.exit(1)
            client.text_to_audio(
                user=args.user,
                message_id=args.message_id,
                text=args.text,
                output=args.output
            )

        elif args.command == 'stop':
            client.stop_message(task_id=args.task_id, user=args.user)

        elif args.command == 'feedback':
            client.message_feedback(
                message_id=args.message_id,
                rating=args.rating,
                user=args.user
            )

        elif args.command == 'create-document':
            client.create_document_by_text(
                dataset_id=args.dataset_id,
                name=args.name,
                text=args.text,
                indexing_technique=args.indexing,
                process_mode=args.process_mode
            )

        elif args.command == 'add-metadata':
            client.add_metadata_field(
                dataset_id=args.dataset_id,
                field_type=args.field_type,
                name=args.name
            )

        elif args.command == 'update-metadata':
            client.update_metadata_field(
                dataset_id=args.dataset_id,
                metadata_id=args.metadata_id,
                name=args.name
            )

        elif args.command == 'delete-metadata':
            client.delete_metadata_field(
                dataset_id=args.dataset_id,
                metadata_id=args.metadata_id
            )

        elif args.command == 'list-metadata':
            client.get_metadata_list(dataset_id=args.dataset_id)

        elif args.command == 'toggle-builtin-metadata':
            client.toggle_builtin_metadata(
                dataset_id=args.dataset_id,
                action=args.action
            )

        print("\n✅ Command completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
