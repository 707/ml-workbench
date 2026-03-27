"""
OpenRouter API client — shared by app.py and tokenizer.py.

Extracted from app.py to avoid circular imports when tokenizer.py
needs to call the OpenRouter API.
"""

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def call_openrouter(
    api_key: str,
    model: str,
    prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict:
    """POST a chat completion request to OpenRouter.

    Args:
        api_key:     OpenRouter API key.
        model:       Model ID string (e.g. "meta-llama/llama-3.1-8b-instruct").
        prompt:      User question string.
        temperature: Sampling temperature — omitted from payload when None.
        max_tokens:  Max completion tokens — omitted from payload when None.

    Returns:
        Parsed JSON response dict.

    Raises:
        requests.HTTPError on non-2xx status.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_models() -> list[dict]:
    """Fetch available models from OpenRouter's public API.

    Returns:
        List of model dicts with id, name, pricing, context_length.

    Raises:
        Exception on HTTP errors.
    """
    resp = requests.get(OPENROUTER_MODELS_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def extract_usage(response: dict) -> dict:
    """Extract token usage counts from an OpenRouter response.

    Returns a dict with keys:
      - prompt_tokens
      - completion_tokens
      - reasoning_tokens  (0 if not present)
    """
    usage = response.get("usage", {})
    details = usage.get("completion_tokens_details", {}) or {}
    reasoning_tokens = details.get("reasoning_tokens") or 0

    return {
        "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
        "completion_tokens": usage.get("completion_tokens", 0) or 0,
        "reasoning_tokens": reasoning_tokens,
    }
