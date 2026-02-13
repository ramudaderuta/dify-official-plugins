import json

from endpoints.llm import (
    _extract_citations,
    _parse_tool_input,
    _split_thinking_blocks,
    _stream_citations_delta,
    _thinking_stream_deltas,
)
from endpoints.tool import (
    collect_text_from_blocks,
    format_web_results,
    format_web_fetch_result,
    tool_result_content,
)


def test_split_thinking_blocks_disabled():
    text = "<think>secret</think>hello"
    blocks = _split_thinking_blocks(text, enable_thinking=False)
    assert blocks == [{"type": "text", "text": text}]


def test_split_thinking_blocks_enabled():
    text = "alpha<think>secret</think>beta"
    blocks = _split_thinking_blocks(text, enable_thinking=True)
    assert blocks == [
        {"type": "text", "text": "alpha"},
        {"type": "thinking", "thinking": "secret", "signature": ""},
        {"type": "text", "text": "beta"},
    ]


def test_split_reasoning_blocks_enabled():
    text = "alpha<reasoning>secret</reasoning>beta"
    blocks = _split_thinking_blocks(text, enable_thinking=True)
    assert blocks == [
        {"type": "text", "text": "alpha"},
        {"type": "thinking", "thinking": "secret", "signature": ""},
        {"type": "text", "text": "beta"},
    ]


def test_parse_tool_input_json():
    payload = {"city": "sf"}
    parsed = _parse_tool_input(json.dumps(payload))
    assert parsed == payload


def test_parse_tool_input_invalid_json():
    parsed = _parse_tool_input("not-json")
    assert parsed == {"_raw": "not-json"}


def test_collect_text_from_blocks():
    blocks = [
        {"type": "text", "text": "hello"},
        {"type": "text", "text": " world"},
    ]
    assert collect_text_from_blocks(blocks) == "hello world"


def test_tool_result_content_text_list():
    block = {
        "type": "tool_result",
        "tool_use_id": "toolu_1",
        "content": [
            {"type": "text", "text": "a"},
            {"type": "text", "text": "b"},
        ],
    }
    assert tool_result_content(block) == "ab"


def test_extract_citations():
    text = "alpha[[cite:source-1]]beta[[cite:source-2]]"
    cleaned, citations = _extract_citations(text)
    assert cleaned == "alphabeta"
    assert citations == [
        {"type": "custom", "reference": "source-1"},
        {"type": "custom", "reference": "source-2"},
    ]


def test_stream_citations_delta_across_chunks():
    pending = ""
    cleaned, citations, pending = _stream_citations_delta("alpha[[ci", pending=pending)
    assert cleaned == "alpha"
    assert citations == []
    assert pending == "[[ci"

    cleaned, citations, pending = _stream_citations_delta("te:src]]beta", pending=pending)
    assert cleaned == "beta"
    assert citations == [{"type": "custom", "reference": "src"}]
    assert pending == ""


def test_format_web_results_with_markers():
    items = [
        {"title": "Result A", "snippet": "Alpha", "url": "https://a.example"},
        {"title": "Result B", "text": "Beta", "url": "https://b.example"},
    ]
    output = format_web_results(items, sources=[{"url": "https://c.example"}])
    assert "Result A" in output
    assert "Alpha" in output
    assert "Result B" in output
    assert "Beta" in output
    assert "[[cite:https://a.example]]" in output
    assert "[[cite:https://b.example]]" in output
    assert "[[cite:https://c.example]]" in output


def test_format_web_fetch_results_with_markers():
    items = [
        {"url": "https://a.example", "title": "Title A", "content": "Alpha"},
        {"url": "https://b.example", "text": "Beta"},
    ]
    output = format_web_fetch_result(items, sources=["https://c.example"])
    assert "https://a.example" in output
    assert "Title A" in output
    assert "Alpha" in output
    assert "https://b.example" in output
    assert "Beta" in output
    assert "[[cite:https://a.example]]" in output
    assert "[[cite:https://b.example]]" in output
    assert "[[cite:https://c.example]]" in output


def _collect_stream_blocks(chunks: list[str]) -> list[tuple[str, str]]:
    pending_buffer = ""
    mode = "text"
    blocks: list[tuple[str, str]] = []
    for chunk in chunks:
        deltas, pending_buffer, mode = _thinking_stream_deltas(
            chunk, pending_buffer=pending_buffer, mode=mode
        )
        blocks.extend(deltas)
    return blocks


def test_thinking_stream_tag_split_across_chunks():
    chunks = ["alpha<thi", "nk>secret</th", "ink>beta"]
    blocks = _collect_stream_blocks(chunks)
    assert blocks == [("text", "alpha"), ("thinking", "secret"), ("text", "beta")]


def test_thinking_stream_close_tag_split_across_chunks():
    chunks = ["alpha<think>secret</th", "ink>beta"]
    blocks = _collect_stream_blocks(chunks)
    assert blocks == [("text", "alpha"), ("thinking", "secret"), ("text", "beta")]


def test_reasoning_stream_tag_split_across_chunks():
    chunks = ["alpha<reas", "oning>secret</re", "asoning>beta"]
    blocks = _collect_stream_blocks(chunks)
    assert blocks == [("text", "alpha"), ("thinking", "secret"), ("text", "beta")]
