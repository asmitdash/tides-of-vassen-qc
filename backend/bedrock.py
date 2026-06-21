import os
import json
from typing import Any, Dict, List, Optional, Callable, Iterator
import boto3
from functools import lru_cache

MODEL_ID = "global.anthropic.claude-opus-4-7"

# TODO: update from current Bedrock pricing
INPUT_PER_MTOK = 15.0
OUTPUT_PER_MTOK = 75.0
CACHE_READ_PER_MTOK = 1.5
CACHE_WRITE_PER_MTOK = 18.75


@lru_cache(maxsize=1)
def client():
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.client("bedrock-runtime", region_name=region)


def call(
    messages: List[Dict[str, Any]],
    system: Optional[Any] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    system_cache: bool = False,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Synchronous call to bedrock with claude-opus-4-7.
    system can be:
      - str (plain system prompt)
      - list of system blocks: [{"type":"text","text":"...", "cache_control": {"type":"ephemeral"}}]
    Returns dict: {text, tool_uses (list), stop_reason, usage}
    """
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": messages,
        "max_tokens": max_tokens,
    }
    # Opus 4.7 1M deprecates `temperature`; do NOT include it.

    if system:
        if isinstance(system, str):
            if system_cache:
                body["system"] = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            else:
                body["system"] = system
        else:
            body["system"] = system

    if tools:
        body["tools"] = tools

    response = client().invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )

    response_body = json.loads(response["body"].read())

    text_blocks = [
        block["text"]
        for block in response_body.get("content", [])
        if block.get("type") == "text"
    ]
    tool_uses = [
        block for block in response_body.get("content", []) if block.get("type") == "tool_use"
    ]

    return {
        "text": "".join(text_blocks),
        "tool_uses": tool_uses,
        "stop_reason": response_body.get("stop_reason"),
        "usage": response_body.get("usage", {}),
    }


def call_streaming(
    messages: List[Dict[str, Any]],
    system: Optional[Any] = None,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> Iterator[bytes]:
    """
    Async generator yielding bytes chunks (text deltas) via bedrock streaming.
    """
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": messages,
        "max_tokens": max_tokens,
    }
    # Opus 4.7 1M deprecates `temperature`.

    if system:
        if isinstance(system, str):
            body["system"] = system
        else:
            body["system"] = system

    response = client().invoke_model_with_response_stream(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )

    for event in response["body"]:
        chunk = event.get("chunk")
        if chunk:
            chunk_data = json.loads(chunk["bytes"])
            if chunk_data.get("type") == "content_block_delta":
                delta = chunk_data.get("delta", {})
                if delta.get("type") == "text_delta":
                    yield delta.get("text", "").encode("utf-8")


def call_tools_loop(
    system: Any,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    tool_handlers: Dict[str, Callable[[Dict[str, Any]], Any]],
    max_rounds: int = 4,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Run a tool-use loop. Returns {text, tool_calls (list), usage (aggregated)}
    """
    accumulated_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    tool_calls = []
    current_messages = list(messages)

    for round_idx in range(max_rounds):
        result = call(
            messages=current_messages,
            system=system,
            tools=tools,
            max_tokens=max_tokens,
        )

        usage = result.get("usage", {})
        for k in accumulated_usage:
            accumulated_usage[k] += usage.get(k, 0)

        if result["stop_reason"] == "end_turn" or not result["tool_uses"]:
            return {
                "text": result["text"],
                "tool_calls": tool_calls,
                "usage": accumulated_usage,
            }

        # Process tool uses
        current_messages.append({"role": "assistant", "content": result["tool_uses"]})

        tool_results = []
        for tool_use in result["tool_uses"]:
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]
            tool_id = tool_use["id"]
            handler = tool_handlers.get(tool_name)
            if handler:
                tool_result = handler(tool_input)
                tool_calls.append(
                    {"name": tool_name, "input": tool_input, "result": tool_result}
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result,
                    }
                )
            else:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Error: no handler for tool {tool_name}",
                        "is_error": True,
                    }
                )

        current_messages.append({"role": "user", "content": tool_results})

    # Max rounds reached
    return {
        "text": "",
        "tool_calls": tool_calls,
        "usage": accumulated_usage,
    }


def estimate_cost(usage: Dict[str, int]) -> float:
    """
    Estimate USD cost from usage dict.
    """
    input_tok = usage.get("input_tokens", 0)
    output_tok = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)

    cost = (
        (input_tok / 1_000_000) * INPUT_PER_MTOK
        + (output_tok / 1_000_000) * OUTPUT_PER_MTOK
        + (cache_read / 1_000_000) * CACHE_READ_PER_MTOK
        + (cache_write / 1_000_000) * CACHE_WRITE_PER_MTOK
    )
    return cost
