from __future__ import annotations

SUPPORTED_PROTOCOLS = {"openai", "anthropic", "gemini", "ollama"}


def normalize_request(body: dict, protocol: str) -> dict:
    """Normalize Anthropic/Gemini/Ollama request to OpenAI-compatible format."""
    if protocol == "openai":
        return body
    if protocol == "anthropic":
        return _anthropic_to_openai(body)
    if protocol == "gemini":
        return _gemini_to_openai(body)
    if protocol == "ollama":
        return _ollama_to_openai(body)
    raise ValueError(f"Unsupported protocol: {protocol}")


def format_response(litellm_response: dict, protocol: str) -> dict:
    """Convert LiteLLM response to the format expected by the client."""
    if protocol == "openai":
        return litellm_response
    if protocol == "anthropic":
        return _openai_to_anthropic(litellm_response)
    if protocol == "gemini":
        return _openai_to_gemini(litellm_response)
    if protocol == "ollama":
        return _openai_to_ollama(litellm_response)
    return litellm_response


def _anthropic_to_openai(body: dict) -> dict:
    messages = list(body.get("messages", []))
    if system := body.get("system"):
        messages.insert(0, {"role": "system", "content": system})
    result: dict = {
        "model": body.get("model", ""),
        "messages": messages,
        "max_tokens": body.get("max_tokens"),
        "temperature": body.get("temperature"),
        "stream": body.get("stream", False),
    }
    if (top_p := body.get("top_p")) is not None:
        result["top_p"] = top_p
    if stop_sequences := body.get("stop_sequences"):
        result["stop"] = stop_sequences
    if tools := body.get("tools"):
        result["tools"] = tools
    if tool_choice := body.get("tool_choice"):
        result["tool_choice"] = tool_choice
    return result


def _gemini_to_openai(body: dict) -> dict:
    contents = body.get("contents", [])
    messages: list[dict] = []
    if system_instruction := body.get("systemInstruction"):
        parts = system_instruction.get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        if text:
            messages.append({"role": "system", "content": text})
    for item in contents:
        role = "user" if item.get("role") == "user" else "assistant"
        text = "".join(p.get("text", "") for p in item.get("parts", []))
        messages.append({"role": role, "content": text})
    return {
        "model": body.get("model", ""),
        "messages": messages,
        "stream": body.get("stream", False),
    }


def _openai_to_anthropic(response: dict) -> dict:
    choice = (response.get("choices") or [{}])[0]
    content = choice.get("message", {}).get("content", "")
    return {
        "id": response.get("id", ""),
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": content}],
        "model": response.get("model", ""),
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": response.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": response.get("usage", {}).get("completion_tokens", 0),
        },
    }


def _openai_to_gemini(response: dict) -> dict:
    choice = (response.get("choices") or [{}])[0]
    content = choice.get("message", {}).get("content", "")
    return {
        "candidates": [{"content": {"parts": [{"text": content}], "role": "model"}, "finishReason": "STOP"}],
        "usageMetadata": {
            "promptTokenCount": response.get("usage", {}).get("prompt_tokens", 0),
            "candidatesTokenCount": response.get("usage", {}).get("completion_tokens", 0),
        },
    }


def _ollama_to_openai(body: dict) -> dict:
    """Map an Ollama /api/chat request to OpenAI chat-completions format.

    Ollama messages already use the {"role", "content"} shape. Generation
    parameters live under an optional "options" object.
    """
    options = body.get("options") or {}
    result: dict = {
        "model": body.get("model", ""),
        "messages": list(body.get("messages", [])),
        "stream": body.get("stream", False),
    }
    if (temperature := options.get("temperature")) is not None:
        result["temperature"] = temperature
    if (top_p := options.get("top_p")) is not None:
        result["top_p"] = top_p
    if (num_predict := options.get("num_predict")) is not None:
        result["max_tokens"] = num_predict
    if (stop := options.get("stop")) is not None:
        result["stop"] = stop
    if tools := body.get("tools"):
        result["tools"] = tools
    return result


def _openai_to_ollama(response: dict) -> dict:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message", {}) or {}
    usage = response.get("usage", {}) or {}
    return {
        "model": response.get("model", ""),
        "created_at": "",
        "message": {
            "role": "assistant",
            "content": message.get("content", "") or "",
        },
        "done": True,
        "done_reason": choice.get("finish_reason", "stop") or "stop",
        "prompt_eval_count": usage.get("prompt_tokens", 0),
        "eval_count": usage.get("completion_tokens", 0),
    }
