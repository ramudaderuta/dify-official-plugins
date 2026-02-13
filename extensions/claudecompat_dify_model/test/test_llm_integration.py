import json

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from endpoints.llm import ClaudeCompatDifyModelEndpoint


class _ToolCallFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, call_id: str, name: str, arguments: str):
        self.id = call_id
        self.type = "function"
        self.function = _ToolCallFunction(name=name, arguments=arguments)


class _Message:
    def __init__(self, content: str, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _Usage:
    def __init__(self, prompt_tokens: int, completion_tokens: int):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _LLMResult:
    def __init__(self, content: str, tool_calls=None):
        self.message = _Message(content=content, tool_calls=tool_calls)
        self.usage = _Usage(prompt_tokens=12, completion_tokens=34)


class _LLMInvoke:
    def __init__(self, result: _LLMResult):
        self._result = result

    def invoke(self, **_kwargs):
        return self._result


class _Model:
    def __init__(self, result: _LLMResult):
        self.llm = _LLMInvoke(result)


class _Session:
    def __init__(self, result: _LLMResult):
        self.model = _Model(result)


def _build_request(payload: dict) -> Request:
    builder = EnvironBuilder(
        method="POST",
        path="/v1/messages",
        data=json.dumps(payload),
        headers={"Authorization": "Bearer test-key"},
        content_type="application/json",
    )
    env = builder.get_environ()
    return Request(env)


def test_blocking_response_with_thinking_and_tool_use():
    tool_calls = [_ToolCall("toolu_1", "get_weather", "{\"city\": \"SF\"}")]
    result = _LLMResult("<think>hidden</think>answer", tool_calls=tool_calls)

    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "thinking": {"type": "enabled", "budget_tokens": 16},
        "messages": [{"role": "user", "content": "Hi"}],
        "tools": [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}},
            }
        ],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={
            "api_key": "test-key",
            "llm": {"model": "kimi-k2.5", "provider": "openai", "mode": "chat"},
        },
    )

    body = json.loads(response.get_data(as_text=True))
    assert body["role"] == "assistant"
    assert body["content"][0]["type"] == "thinking"
    assert body["content"][1]["type"] == "text"
    assert body["content"][2]["type"] == "tool_use"
    assert body["stop_reason"] == "tool_use"


def test_rejects_output_format():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "output_format": {"type": "json_schema", "json_schema": {"name": "X"}},
        "messages": [{"role": "user", "content": "Hi"}],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert response.status_code == 400
    body = json.loads(response.get_data(as_text=True))
    assert body["error"]["type"] == "invalid_request_error"


def test_rejects_betas():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "betas": ["structured-outputs-2025-11-13"],
        "messages": [{"role": "user", "content": "Hi"}],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert response.status_code == 400
    body = json.loads(response.get_data(as_text=True))
    assert body["error"]["type"] == "invalid_request_error"


def test_rejects_strict_tool():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "messages": [{"role": "user", "content": "Hi"}],
        "tools": [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}},
                "strict": True,
            }
        ],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert response.status_code == 400
    body = json.loads(response.get_data(as_text=True))
    assert body["error"]["type"] == "invalid_request_error"


def test_tool_result_requires_matching_tool_use():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "messages": [
            {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {}}],
            },
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"}],
            },
        ],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert response.status_code == 200

    bad_payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "toolu_missing", "content": "ok"}],
            }
        ],
    }

    bad_response = endpoint._invoke(
        _build_request(bad_payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert bad_response.status_code == 400


def test_tool_use_requires_name_and_known_tool():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    missing_name_payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "messages": [
            {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "toolu_1", "input": {}}],
            }
        ],
    }

    response = endpoint._invoke(
        _build_request(missing_name_payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert response.status_code == 400

    unknown_tool_payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "toolu_1", "name": "missing", "input": {}}
                ],
            }
        ],
        "tools": [
            {
                "name": "known",
                "description": "Known tool",
                "input_schema": {"type": "object", "properties": {}},
            }
        ],
    }

    bad_response = endpoint._invoke(
        _build_request(unknown_tool_payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert bad_response.status_code == 400


def test_web_search_tool_result_mapping():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 64,
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "toolu_1", "name": "web_search", "input": {}}
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "web_search_tool_result",
                        "tool_use_id": "toolu_1",
                        "content": [
                            {"title": "Doc", "snippet": "Info", "url": "https://d.example"}
                        ],
                    }
                ],
            },
        ],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert response.status_code == 200


def test_web_fetch_tool_result_mapping():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 64,
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "toolu_1", "name": "web_fetch", "input": {}}
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "web_fetch_tool_result",
                        "tool_use_id": "toolu_1",
                        "content": [
                            {"url": "https://d.example", "title": "Doc", "content": "Info"}
                        ],
                    }
                ],
            },
        ],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai"}},
    )
    assert response.status_code == 200


def test_allowed_models_rejects_unknown():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "glm-4.9",
        "max_tokens": 64,
        "messages": [{"role": "user", "content": "Hi"}],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={
            "api_key": "test-key",
            "llm": {"model": "kimi-k2.5", "provider": "openai"},
            "allowed_models": "kimi-k2.5,glm-4.8",
        },
    )
    assert response.status_code == 400


def test_missing_max_tokens_uses_default():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "messages": [{"role": "user", "content": "Hi"}],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={
            "api_key": "test-key",
            "llm": {
                "model": "kimi-k2.5",
                "provider": "openai",
                "completion_params": {"max_tokens": 128},
            },
        },
    )
    assert response.status_code == 200


def test_thinking_defaults_from_model_selector():
    tool_calls = []
    result = _LLMResult("<think>hidden</think>answer", tool_calls=tool_calls)
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 128,
        "messages": [{"role": "user", "content": "Hi"}],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={
            "api_key": "test-key",
            "llm": {
                "model": "kimi-k2.5",
                "provider": "openai",
                "mode": "chat",
                "completion_params": {"thinking": {"type": "enabled", "budget_tokens": 32}},
            },
        },
    )
    body = json.loads(response.get_data(as_text=True))
    assert body["content"][0]["type"] == "thinking"


def test_request_params_override_defaults():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 64,
        "temperature": 0.9,
        "top_p": 0.8,
        "messages": [{"role": "user", "content": "Hi"}],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={
            "api_key": "test-key",
            "llm": {
                "model": "kimi-k2.5",
                "provider": "openai",
                "mode": "chat",
                "completion_params": {"max_tokens": 256, "temperature": 0.1, "top_p": 0.2},
            },
        },
    )
    assert response.status_code == 200
    assert response.status_code == 200


def test_inserts_user_fallback_for_tool_only():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 64,
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {}}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "toolu_1", "content": "Sunny"}
                ],
            },
        ],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai", "mode": "chat"}},
    )
    assert response.status_code == 200


def test_inserts_user_fallback_for_tool_result_only_user_role():
    result = _LLMResult("ok")
    endpoint = ClaudeCompatDifyModelEndpoint(_Session(result))

    payload = {
        "model": "kimi-k2.5",
        "max_tokens": 64,
        "messages": [
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {}}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "toolu_1", "content": "Sunny"}
                ],
            },
        ],
    }

    response = endpoint._invoke(
        _build_request(payload),
        values={},
        settings={"api_key": "test-key", "llm": {"model": "kimi-k2.5", "provider": "openai", "mode": "chat"}},
    )
    assert response.status_code == 200
