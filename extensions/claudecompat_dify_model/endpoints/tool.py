from __future__ import annotations

import json
from typing import Any

from dify_plugin.entities.invoke_message import InvokeMessage
from dify_plugin.entities.tool import ToolProviderType


def collect_text_from_blocks(blocks: list[dict]) -> str:
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            raise ValueError("content blocks must be objects")
        if block.get("type") != "text":
            raise ValueError("content blocks must be text")
        parts.append(str(block.get("text", "")))
    return "".join(parts)


def tool_result_content(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return append_sources_markers(content, block.get("sources"))
    if isinstance(content, list):
        if looks_like_web_results(content):
            return format_web_results(content, block.get("sources"))
        if looks_like_web_fetch_result(content):
            return format_web_fetch_result(content, block.get("sources"))
        return append_sources_markers(
            collect_text_from_blocks(content), block.get("sources")
        )
    raise ValueError("tool_result content must be string or list of text blocks")


def append_sources_markers(text: str, sources: Any) -> str:
    if not sources:
        return text
    markers: list[str] = []
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, str):
                marker = source.strip()
            elif isinstance(source, dict):
                marker = str(source.get("url") or source.get("id") or "").strip()
            else:
                marker = ""
            if marker:
                markers.append(f"[[cite:{marker}]]")
    if not markers:
        return text
    suffix = " " + " ".join(markers)
    return f"{text}{suffix}"


def looks_like_web_results(items: list) -> bool:
    if not items:
        return False
    for item in items:
        if not isinstance(item, dict):
            return False
        if "type" in item:
            return False
        if "url" not in item and "title" not in item and "snippet" not in item and "text" not in item:
            return False
    return True


def looks_like_web_fetch_result(items: list) -> bool:
    if not items:
        return False
    for item in items:
        if not isinstance(item, dict):
            return False
        if "type" in item:
            return False
        if "url" not in item and "content" not in item and "text" not in item and "html" not in item:
            return False
    return True


def format_web_results(items: list[dict], sources: Any) -> str:
    lines: list[str] = []
    extra_sources: list[str] = []
    for item in items:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("snippet") or item.get("text") or "").strip()
        if title:
            lines.append(title)
        if snippet:
            lines.append(snippet)
        if url:
            extra_sources.append(url)
        lines.append("")
    content = "\n".join(lines).strip()
    combined_sources = []
    if isinstance(sources, list):
        combined_sources.extend(sources)
    if extra_sources:
        combined_sources.extend(extra_sources)
    return append_sources_markers(content, combined_sources)


def format_web_fetch_result(items: list[dict], sources: Any) -> str:
    lines: list[str] = []
    extra_sources: list[str] = []
    for item in items:
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        content = str(item.get("content") or item.get("text") or item.get("html") or "").strip()
        if url:
            lines.append(url)
        if title:
            lines.append(title)
        if content:
            lines.append(content)
        if url:
            extra_sources.append(url)
        lines.append("")
    merged = "\n".join(lines).strip()
    combined_sources = []
    if isinstance(sources, list):
        combined_sources.extend(sources)
    if extra_sources:
        combined_sources.extend(extra_sources)
    return append_sources_markers(merged, combined_sources)


def invoke_tool_and_collect_text(
    session,
    provider_type: str,
    provider: str,
    tool_name: str,
    parameters: dict[str, Any],
    credential_id: str | None = None,
) -> str:
    provider_enum = ToolProviderType.value_of(provider_type)
    if provider_enum == ToolProviderType.BUILT_IN:
        generator = session.tool.invoke_builtin_tool(provider, tool_name, parameters)
    elif provider_enum == ToolProviderType.API:
        generator = session.tool.invoke_api_tool(provider, tool_name, parameters)
    elif provider_enum == ToolProviderType.WORKFLOW:
        generator = session.tool.invoke_workflow_tool(provider, tool_name, parameters)
    else:
        generator = session.tool.invoke(provider_enum, provider, tool_name, parameters, credential_id)

    parts: list[str] = []
    for message in generator:
        if message.type == InvokeMessage.MessageType.TEXT and message.message:
            parts.append(str(message.message.text))
            continue
        if message.type == InvokeMessage.MessageType.JSON and message.message:
            parts.append(json.dumps(message.message.json_object, ensure_ascii=False))
            continue
        if message.type == InvokeMessage.MessageType.VARIABLE and message.message:
            parts.append(str(message.message.variable_value))
            continue
        if isinstance(message.message, dict):
            parts.append(json.dumps(message.message, ensure_ascii=False))
            continue
    return "\n".join([p for p in parts if p])
