import json
import re
import uuid
from typing import Iterable, Mapping, Optional

from dify_plugin import Endpoint
from dify_plugin.entities.model.llm import LLMModelConfig
from dify_plugin.entities.model.message import (
    AssistantPromptMessage,
    PromptMessage,
    PromptMessageTool,
    SystemPromptMessage,
    ToolPromptMessage,
    UserPromptMessage,
)
from werkzeug import Request, Response

from endpoints.auth import BaseAuth
from endpoints.tool import (
    collect_text_from_blocks,
    invoke_tool_and_collect_text,
    tool_result_content,
)


def _error_response(
    message: str, status: int = 400, *, error_type: str = "invalid_request_error"
) -> Response:
    return Response(
        json.dumps({"error": {"type": error_type, "message": message}}),
        status=status,
        content_type="application/json",
    )


def _parse_tool_input(arguments: str) -> dict:
    if not arguments:
        return {}
    try:
        parsed = json.loads(arguments)
        if isinstance(parsed, dict):
            return parsed
        return {"_raw": parsed}
    except json.JSONDecodeError:
        return {"_raw": arguments}


def _split_thinking_blocks(text: str, enable_thinking: bool) -> list[dict]:
    if not text:
        return []
    if not enable_thinking:
        return [{"type": "text", "text": text}]

    blocks: list[dict] = []
    cursor = 0
    while cursor < len(text):
        think_start = text.find("<think>", cursor)
        reasoning_start = text.find("<reasoning>", cursor)
        if think_start == -1 and reasoning_start == -1:
            remaining = text[cursor:]
            if remaining:
                blocks.append({"type": "text", "text": remaining})
            break
        if reasoning_start == -1 or (think_start != -1 and think_start < reasoning_start):
            start = think_start
            open_tag = "<think>"
            close_tag = "</think>"
        else:
            start = reasoning_start
            open_tag = "<reasoning>"
            close_tag = "</reasoning>"
        if start > cursor:
            blocks.append({"type": "text", "text": text[cursor:start]})
        end = text.find(close_tag, start + len(open_tag))
        if end == -1:
            remaining = text[start:]
            if remaining:
                blocks.append({"type": "text", "text": remaining})
            break
        thinking = text[start + len(open_tag) : end]
        if thinking:
            blocks.append(
                {
                    "type": "thinking",
                    "thinking": thinking,
                    "signature": "",
                }
            )
        cursor = end + len(close_tag)
    return blocks


_CITATION_PATTERN = re.compile(r"\[\[cite:(.+?)\]\]")


def _extract_citations(text: str) -> tuple[str, list[dict]]:
    if not text:
        return text, []
    citations: list[dict] = []

    def _replace(match: re.Match) -> str:
        ref = match.group(1).strip()
        if ref:
            citations.append({"type": "custom", "reference": ref})
        return ""

    cleaned = _CITATION_PATTERN.sub(_replace, text)
    return cleaned, citations


def _stream_citations_delta(
    text: str, *, pending: str
) -> tuple[str, list[dict], str]:
    buffer = pending + text
    if not buffer:
        return "", [], ""

    output_parts: list[str] = []
    citations: list[dict] = []
    cursor = 0
    marker = "[[cite:"
    while cursor < len(buffer):
        start = buffer.find(marker, cursor)
        if start == -1:
            remaining = buffer[cursor:]
            keep_len = 0
            max_keep = min(len(marker) - 1, len(remaining))
            for size in range(1, max_keep + 1):
                if remaining.endswith(marker[:size]):
                    keep_len = size
            emit_text = remaining[:-keep_len] if keep_len else remaining
            if emit_text:
                output_parts.append(emit_text)
            buffer = remaining[-keep_len:] if keep_len else ""
            break
        if start > cursor:
            output_parts.append(buffer[cursor:start])
        end = buffer.find("]]", start + len(marker))
        if end == -1:
            buffer = buffer[start:]
            break
        ref = buffer[start + len(marker) : end].strip()
        if ref:
            citations.append({"type": "custom", "reference": ref})
        cursor = end + 2
        if cursor >= len(buffer):
            buffer = ""
            break

    if buffer and not buffer.startswith(marker) and not marker.startswith(buffer):
        output_parts.append(buffer)
        buffer = ""

    return "".join(output_parts), citations, buffer


def _apply_citations_to_blocks(blocks: list[dict]) -> list[dict]:
    if not blocks:
        return blocks
    updated: list[dict] = []
    for block in blocks:
        if block.get("type") != "text":
            updated.append(block)
            continue
        cleaned, citations = _extract_citations(str(block.get("text", "")))
        new_block = dict(block)
        new_block["text"] = cleaned
        if citations:
            new_block["citations"] = citations
        updated.append(new_block)
    return updated


def _collect_text_from_blocks(blocks: list[dict]) -> str:
    return collect_text_from_blocks(blocks)


def _parse_allowed_models(value) -> set[str]:
    if not value:
        return set()
    if isinstance(value, list):
        return {str(v).strip() for v in value if str(v).strip()}
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return set()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return {str(v).strip() for v in parsed if str(v).strip()}
            except json.JSONDecodeError:
                return set()
        return {v.strip() for v in text.split(",") if v.strip()}
    return set()


def _thinking_stream_deltas(
    chunk_text: str, *, pending_buffer: str, mode: str
) -> tuple[list[tuple[str, str]], str, str]:
    pending_buffer += chunk_text
    output: list[tuple[str, str]] = []
    while pending_buffer:
        if mode == "text":
            think_tag = "<think>"
            reasoning_tag = "<reasoning>"
            think_index = pending_buffer.find(think_tag)
            reasoning_index = pending_buffer.find(reasoning_tag)
            if think_index == -1 and reasoning_index == -1:
                tag = think_tag
                keep_len = 0
                max_keep = min(len(tag) - 1, len(pending_buffer))
                for size in range(1, max_keep + 1):
                    if pending_buffer.endswith(tag[:size]) or pending_buffer.endswith(reasoning_tag[:size]):
                        keep_len = size
                emit_text = pending_buffer[:-keep_len] if keep_len else pending_buffer
                if emit_text:
                    output.append(("text", emit_text))
                if keep_len and keep_len == len(pending_buffer):
                    break
                pending_buffer = pending_buffer[-keep_len:] if keep_len else ""
            else:
                if reasoning_index == -1 or (think_index != -1 and think_index < reasoning_index):
                    tag_index = think_index
                    tag = think_tag
                else:
                    tag_index = reasoning_index
                    tag = reasoning_tag
                before = pending_buffer[:tag_index]
                if before:
                    output.append(("text", before))
                pending_buffer = pending_buffer[tag_index + len(tag) :]
                mode = "thinking"
        else:
            think_tag = "</think>"
            reasoning_tag = "</reasoning>"
            end_think = pending_buffer.find(think_tag)
            end_reasoning = pending_buffer.find(reasoning_tag)
            if end_think == -1 and end_reasoning == -1:
                tag = think_tag
                keep_len = 0
                max_keep = min(len(tag) - 1, len(pending_buffer))
                for size in range(1, max_keep + 1):
                    if pending_buffer.endswith(tag[:size]) or pending_buffer.endswith(reasoning_tag[:size]):
                        keep_len = size
                emit_text = pending_buffer[:-keep_len] if keep_len else pending_buffer
                if emit_text:
                    output.append(("thinking", emit_text))
                if keep_len and keep_len == len(pending_buffer):
                    break
                pending_buffer = pending_buffer[-keep_len:] if keep_len else ""
            else:
                if end_reasoning == -1 or (end_think != -1 and end_think < end_reasoning):
                    end_index = end_think
                    tag = think_tag
                else:
                    end_index = end_reasoning
                    tag = reasoning_tag
                thinking_chunk = pending_buffer[:end_index]
                if thinking_chunk:
                    output.append(("thinking", thinking_chunk))
                pending_buffer = pending_buffer[end_index + len(tag) :]
                mode = "text"
            if mode == "text":
                continue
    return output, pending_buffer, mode


class ClaudeCompatDifyModelEndpoint(Endpoint, BaseAuth):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        if not self.verify(r, settings):
            return _error_response(
                "Unauthorized", status=401, error_type="authentication_error"
            )

        llm: Optional[dict] = settings.get("llm")
        if not llm:
            return _error_response("LLM is not set", status=400)

        if "completion_params" not in llm:
            llm["completion_params"] = {}

        data = r.get_json(force=True)
        if not data:
            return _error_response("Request body is empty", status=400)

        model = data.get("model") or llm.get("model")
        if not model:
            return _error_response("Model is required", status=400)
        allowed_models = _parse_allowed_models(settings.get("allowed_models"))
        if allowed_models and model not in allowed_models:
            return _error_response("Model is not allowed", status=400)
        llm["model"] = model

        max_tokens = data.get("max_tokens")
        if max_tokens is None:
            if "max_tokens" not in llm["completion_params"]:
                return _error_response("max_tokens is required", status=400)
        else:
            llm["completion_params"]["max_tokens"] = max_tokens

        if "output_format" in data:
            return _error_response("output_format is not supported", status=400)

        betas = data.get("betas")
        if betas:
            return _error_response("betas are not supported", status=400)

        for key in ("temperature", "top_p"):
            if key in data:
                llm["completion_params"][key] = data[key]

        tool_auto = bool(data.get("tool_auto", False))
        tool_invocation = data.get("tool_invocation")
        if tool_invocation is not None and not isinstance(tool_invocation, dict):
            return _error_response("tool_invocation must be an object", status=400)

        thinking = data.get("thinking")
        default_thinking = llm.get("completion_params", {}).get("thinking")
        if thinking is None and isinstance(default_thinking, dict):
            thinking = dict(default_thinking)
        if thinking is None:
            thinking = {}
        if isinstance(thinking, dict) and isinstance(default_thinking, dict):
            if "budget_tokens" not in thinking and "budget_tokens" in default_thinking:
                thinking["budget_tokens"] = default_thinking["budget_tokens"]
            if "type" not in thinking and "type" in default_thinking:
                thinking["type"] = default_thinking["type"]
        enable_thinking = bool(
            isinstance(thinking, dict) and thinking.get("type") == "enabled"
        )

        tools: list[PromptMessageTool] = []
        tool_names: set[str] = set()
        if data.get("tools"):
            for tool in data.get("tools", []):
                if not isinstance(tool, dict):
                    return _error_response("tools must be objects", status=400)
                name = tool.get("name")
                description = tool.get("description")
                input_schema = tool.get("input_schema")
                if tool.get("strict") is True:
                    return _error_response("tool strict mode is not supported", status=400)
                if not name or not description or not isinstance(input_schema, dict):
                    return _error_response("tool requires name, description, input_schema", status=400)
                tools.append(
                    PromptMessageTool(name=name, description=description, parameters=input_schema)
                )
                tool_names.add(str(name))

        messages = data.get("messages")
        if not isinstance(messages, list) or not messages:
            return _error_response("messages must be a non-empty list", status=400)

        prompt_messages: list[PromptMessage] = []

        system = data.get("system")
        if system:
            if isinstance(system, str):
                prompt_messages.append(SystemPromptMessage(content=system))
            elif isinstance(system, list):
                try:
                    system_text = _collect_text_from_blocks(system)
                except ValueError as exc:
                    return _error_response(str(exc), status=400)
                prompt_messages.append(SystemPromptMessage(content=system_text))
            else:
                return _error_response("system must be string or list of text blocks", status=400)

        needs_user_fallback = True
        has_user_text = False
        seen_tool_use_ids: dict[str, str] = {}
        provided_tool_result_ids: set[str] = set()
        for message in messages:
            if message.get("role") == "user":
                needs_user_fallback = False
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if block_type in ("tool_result", "web_search_tool_result", "web_fetch_tool_result"):
                    tool_use_id = block.get("tool_use_id")
                    if tool_use_id:
                        provided_tool_result_ids.add(str(tool_use_id))

        def resolve_tool_route(tool_name: str) -> dict | None:
            if tool_invocation and tool_name in tool_invocation:
                return tool_invocation.get(tool_name)
            if tool_name == "web_fetch":
                return {
                    "provider_type": "builtin",
                    "provider": "webscraper",
                    "tool": "webscraper",
                }
            return None

        for message in messages:
            role = message.get("role")
            if role not in ("user", "assistant"):
                return _error_response(f"Invalid role: {role}", status=400)

            content = message.get("content")
            text_parts: list[str] = []
            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        return _error_response("content blocks must be objects", status=400)
                    block_type = block.get("type")
                    if block_type == "text":
                        text_parts.append(str(block.get("text", "")))
                    elif block_type == "tool_use":
                        if role != "assistant":
                            return _error_response(
                                "tool_use blocks are only allowed for assistant role", status=400
                            )
                        tool_id = block.get("id")
                        tool_name = block.get("name")
                        if not tool_id:
                            return _error_response("tool_use.id is required", status=400)
                        if not tool_name:
                            return _error_response("tool_use.name is required", status=400)
                        if tool_names and str(tool_name) not in tool_names:
                            return _error_response(
                                "tool_use.name is not defined in tools", status=400
                            )
                        seen_tool_use_ids[str(tool_id)] = str(tool_name)
                        if tool_auto and str(tool_id) not in provided_tool_result_ids:
                            route = resolve_tool_route(str(tool_name))
                            if route:
                                if not isinstance(route, dict):
                                    return _error_response(
                                        "tool_invocation entries must be objects", status=400
                                    )
                                provider_type = route.get("provider_type")
                                provider = route.get("provider")
                                tool = route.get("tool")
                                credential_id = route.get("credential_id")
                                if not provider_type or not provider or not tool:
                                    return _error_response(
                                        "tool_invocation entry requires provider_type, provider, tool",
                                        status=400,
                                    )
                                tool_input = block.get("input")
                                if tool_input is None:
                                    tool_input = {}
                                if not isinstance(tool_input, dict):
                                    return _error_response(
                                        "tool_use.input must be an object when tool_auto is enabled",
                                        status=400,
                                    )
                                if text_parts:
                                    text = "".join(text_parts)
                                    prompt_messages.append(AssistantPromptMessage(content=text))
                                    text_parts = []
                                try:
                                    tool_output = invoke_tool_and_collect_text(
                                        self.session,
                                        str(provider_type),
                                        str(provider),
                                        str(tool),
                                        tool_input,
                                        credential_id=credential_id,
                                    )
                                except Exception as exc:
                                    return _error_response(
                                        f"tool invocation failed: {exc}", status=400
                                    )
                                prompt_messages.append(
                                    ToolPromptMessage(
                                        content=tool_output,
                                        tool_call_id=str(tool_id),
                                    )
                                )
                            elif str(tool_name) in ("web_search", "web_fetch"):
                                return _error_response(
                                    "tool_invocation mapping required for tool_auto",
                                    status=400,
                                )
                    elif block_type == "tool_result":
                        if role != "user":
                            return _error_response(
                                "tool_result blocks are only allowed for user role", status=400
                            )
                        tool_use_id = block.get("tool_use_id")
                        if not tool_use_id:
                            return _error_response("tool_result.tool_use_id is required", status=400)
                        tool_use_id_str = str(tool_use_id)
                        if tool_use_id_str not in seen_tool_use_ids:
                            return _error_response(
                                "tool_result.tool_use_id has no matching tool_use", status=400
                            )
                        tool_result_name = block.get("tool_name") or block.get("name")
                        if tool_result_name:
                            expected_name = seen_tool_use_ids.get(tool_use_id_str)
                            if expected_name and str(tool_result_name) != expected_name:
                                return _error_response(
                                    "tool_result tool name does not match tool_use", status=400
                                )
                        try:
                            tool_content = tool_result_content(block)
                        except ValueError as exc:
                            return _error_response(str(exc), status=400)
                        prompt_messages.append(
                            ToolPromptMessage(content=tool_content, tool_call_id=str(tool_use_id))
                        )
                    elif block_type == "web_search_tool_result":
                        if role != "user":
                            return _error_response(
                                "web_search_tool_result blocks are only allowed for user role",
                                status=400,
                            )
                        tool_use_id = block.get("tool_use_id")
                        if not tool_use_id:
                            return _error_response(
                                "web_search_tool_result.tool_use_id is required", status=400
                            )
                        tool_use_id_str = str(tool_use_id)
                        if tool_use_id_str not in seen_tool_use_ids:
                            return _error_response(
                                "web_search_tool_result.tool_use_id has no matching tool_use",
                                status=400,
                            )
                        try:
                            tool_content = tool_result_content(block)
                        except ValueError as exc:
                            return _error_response(str(exc), status=400)
                        prompt_messages.append(
                            ToolPromptMessage(content=tool_content, tool_call_id=tool_use_id_str)
                        )
                    elif block_type == "web_fetch_tool_result":
                        if role != "user":
                            return _error_response(
                                "web_fetch_tool_result blocks are only allowed for user role",
                                status=400,
                            )
                        tool_use_id = block.get("tool_use_id")
                        if not tool_use_id:
                            return _error_response(
                                "web_fetch_tool_result.tool_use_id is required", status=400
                            )
                        tool_use_id_str = str(tool_use_id)
                        if tool_use_id_str not in seen_tool_use_ids:
                            return _error_response(
                                "web_fetch_tool_result.tool_use_id has no matching tool_use",
                                status=400,
                            )
                        try:
                            tool_content = tool_result_content(block)
                        except ValueError as exc:
                            return _error_response(str(exc), status=400)
                        prompt_messages.append(
                            ToolPromptMessage(content=tool_content, tool_call_id=tool_use_id_str)
                        )
                    else:
                        return _error_response(
                            f"Unsupported content block type: {block_type}", status=400
                        )
            else:
                return _error_response("content must be string or list of blocks", status=400)

            if text_parts:
                text = "".join(text_parts)
                if role == "user":
                    needs_user_fallback = False
                    if text.strip():
                        has_user_text = True
                    prompt_messages.append(UserPromptMessage(content=text))
                else:
                    prompt_messages.append(AssistantPromptMessage(content=text))

        if needs_user_fallback or not has_user_text:
            prompt_messages.insert(
                0,
                UserPromptMessage(
                    content="Use the tool results provided to answer the user."
                ),
            )

        stream: bool = data.get("stream", False)

        def _build_usage(usage) -> dict:
            if not usage:
                return {"input_tokens": 0, "output_tokens": 0}
            return {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
            }

        def _map_stop_reason(has_tool_calls: bool, finish_reason: Optional[str]) -> str:
            if finish_reason == "length":
                return "max_tokens"
            if finish_reason == "stop_sequence":
                return "stop_sequence"
            if has_tool_calls:
                return "tool_use"
            return "end_turn"

        def generator():
            if not stream:
                llm_invoke_response = self.session.model.llm.invoke(
                    model_config=LLMModelConfig(**llm),
                    prompt_messages=prompt_messages,
                    tools=tools,
                    stream=False,
                )

                text_content = llm_invoke_response.message.content or ""
                blocks = _apply_citations_to_blocks(
                    _split_thinking_blocks(text_content, enable_thinking)
                )

                tool_calls = llm_invoke_response.message.tool_calls or []
                for tool_call in tool_calls:
                    tool_id = tool_call.id or f"toolu_{uuid.uuid4().hex}"
                    tool_input = _parse_tool_input(tool_call.function.arguments)
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": tool_call.function.name,
                            "input": tool_input,
                        }
                    )

                finish_reason = getattr(llm_invoke_response, "finish_reason", None)
                if not finish_reason:
                    finish_reason = getattr(llm_invoke_response.message, "finish_reason", None)

                response_body = {
                    "id": f"msg_{uuid.uuid4().hex}",
                    "type": "message",
                    "role": "assistant",
                    "model": llm.get("model"),
                    "content": blocks,
                    "stop_reason": _map_stop_reason(bool(tool_calls), finish_reason),
                    "stop_sequence": None,
                    "usage": _build_usage(llm_invoke_response.usage),
                }
                yield json.dumps(response_body)
                return

            response_id = f"msg_{uuid.uuid4().hex}"
            current_index = -1
            current_block_type: Optional[str] = None
            pending_buffer = ""
            mode = "text"

            def start_block(block_type: str, *, tool_meta: Optional[dict] = None):
                nonlocal current_index, current_block_type
                current_index += 1
                current_block_type = block_type
                if block_type == "thinking":
                    content_block = {"type": "thinking", "thinking": "", "signature": ""}
                elif block_type == "tool_use":
                    tool_meta = tool_meta or {}
                    content_block = {
                        "type": "tool_use",
                        "id": tool_meta.get("id", ""),
                        "name": tool_meta.get("name", ""),
                        "input": {},
                    }
                else:
                    content_block = {"type": "text", "text": ""}
                event = {
                    "type": "content_block_start",
                    "index": current_index,
                    "content_block": content_block,
                }
                yield f"data: {json.dumps(event)}\n\n"

            def stop_block():
                event = {"type": "content_block_stop", "index": current_index}
                yield f"data: {json.dumps(event)}\n\n"

            def emit_block_delta(text_delta: str):
                if not text_delta:
                    return
                if current_block_type == "thinking":
                    delta = {"type": "thinking_delta", "thinking": text_delta}
                else:
                    delta = {"type": "text_delta", "text": text_delta}
                event = {
                    "type": "content_block_delta",
                    "index": current_index,
                    "delta": delta,
                }
                yield f"data: {json.dumps(event)}\n\n"

            def emit_citation_delta(citation: dict):
                if not citation:
                    return
                event = {
                    "type": "content_block_delta",
                    "index": current_index,
                    "delta": {"type": "citations_delta", "citation": citation},
                }
                yield f"data: {json.dumps(event)}\n\n"

            def emit_signature_delta(signature: str = ""):
                event = {
                    "type": "content_block_delta",
                    "index": current_index,
                    "delta": {"type": "signature_delta", "signature": signature},
                }
                yield f"data: {json.dumps(event)}\n\n"

            def emit_input_json_delta(delta: str):
                if not delta:
                    return
                event = {
                    "type": "content_block_delta",
                    "index": current_index,
                    "delta": {"type": "input_json_delta", "partial_json": delta},
                }
                yield f"data: {json.dumps(event)}\n\n"

            def emit_input_json_chunks(payload: str, *, chunk_size: int = 512):
                if not payload:
                    return
                for i in range(0, len(payload), chunk_size):
                    chunk = payload[i : i + chunk_size]
                    for event in emit_input_json_delta(chunk):
                        yield event

            def emit_message_start():
                event = {
                    "type": "message_start",
                    "message": {
                        "id": response_id,
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": llm.get("model"),
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                    },
                }
                return f"data: {json.dumps(event)}\n\n"

            pending_citation = ""

            def emit_text_with_citations(text_delta: str):
                nonlocal pending_citation
                cleaned, citations, pending_citation = _stream_citations_delta(
                    text_delta, pending=pending_citation
                )
                if cleaned:
                    for event in emit_block_delta(cleaned):
                        yield event
                if citations:
                    for citation in citations:
                        for event in emit_citation_delta(citation):
                            yield event

            def process_thinking_stream(chunk_text: str) -> Iterable[str]:
                nonlocal pending_buffer, mode, current_block_type, pending_citation
                output_events: list[str] = []
                deltas, pending_buffer, mode = _thinking_stream_deltas(
                    chunk_text, pending_buffer=pending_buffer, mode=mode
                )
                for delta_type, delta_text in deltas:
                    if current_block_type != delta_type:
                        if current_block_type is not None:
                            if current_block_type == "text" and pending_citation:
                                output_events.extend(list(emit_text_with_citations(pending_citation)))
                                pending_citation = ""
                            if current_block_type == "thinking":
                                output_events.extend(list(emit_signature_delta()))
                            output_events.extend(stop_block())
                        output_events.extend(start_block(delta_type))
                    if delta_type == "text":
                        output_events.extend(list(emit_text_with_citations(delta_text)))
                    else:
                        output_events.extend(emit_block_delta(delta_text))
                return output_events

            llm_invoke_response = self.session.model.llm.invoke(
                model_config=LLMModelConfig(**llm),
                prompt_messages=prompt_messages,
                tools=tools,
                stream=True,
            )

            yield emit_message_start()

            tool_calls: list[AssistantPromptMessage.ToolCall] = []
            finish_reason = None

            for chunk in llm_invoke_response:
                if chunk.delta.finish_reason:
                    finish_reason = chunk.delta.finish_reason
                if chunk.delta.message.tool_calls:
                    tool_calls = chunk.delta.message.tool_calls

                delta_content = chunk.delta.message.content
                if not delta_content:
                    continue

                if enable_thinking:
                    for event in process_thinking_stream(delta_content):
                        yield event
                else:
                    if current_block_type != "text":
                        if current_block_type is not None:
                            for event in stop_block():
                                yield event
                        for event in start_block("text"):
                            yield event
                    for event in emit_text_with_citations(delta_content):
                        yield event

            if enable_thinking and pending_buffer:
                final_type = "thinking" if mode == "thinking" else "text"
                if current_block_type != final_type:
                    if current_block_type is not None:
                        for event in stop_block():
                            yield event
                    for event in start_block(final_type):
                        yield event
                if final_type == "text":
                    for event in emit_text_with_citations(pending_buffer):
                        yield event
                else:
                    for event in emit_block_delta(pending_buffer):
                        yield event
                pending_buffer = ""

            if current_block_type == "text" and pending_citation:
                for event in emit_text_with_citations(pending_citation):
                    yield event
                pending_citation = ""

            if current_block_type is not None:
                if current_block_type == "thinking":
                    for event in emit_signature_delta():
                        yield event
                for event in stop_block():
                    yield event

            for tool_call in tool_calls:
                tool_id = tool_call.id or f"toolu_{uuid.uuid4().hex}"
                tool_name = tool_call.function.name
                for event in start_block("tool_use", tool_meta={"id": tool_id, "name": tool_name}):
                    yield event
                tool_payload = {
                    **_parse_tool_input(tool_call.function.arguments),
                }
                for event in emit_input_json_chunks(json.dumps(tool_payload)):
                    yield event
                for event in stop_block():
                    yield event

            stop_reason = "end_turn"
            if finish_reason == "length":
                stop_reason = "max_tokens"
            if finish_reason == "stop_sequence":
                stop_reason = "stop_sequence"
            if tool_calls:
                stop_reason = "tool_use"

            message_delta = {
                "type": "message_delta",
                "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            }
            yield f"data: {json.dumps(message_delta)}\n\n"
            yield "data: {\"type\": \"message_stop\"}\n\n"

        return Response(
            generator(),
            status=200,
            content_type="text/event-stream" if stream else "application/json",
        )
