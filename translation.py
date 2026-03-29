"""
Translation module — wraps OpenRouter for text-to-English translation.

Provides a single public function with LRU caching to avoid redundant
API calls for identical inputs.
"""

import functools

from openrouter import call_openrouter

_TRANSLATION_MODEL = "meta-llama/llama-3.1-8b-instruct"


@functools.lru_cache(maxsize=128)
def translate_to_english(text: str, api_key: str) -> str:
    """Translate text to English using OpenRouter.

    Results are LRU-cached by (text, api_key) to avoid redundant API calls.

    Args:
        text:    Source text to translate.
        api_key: OpenRouter API key.

    Returns:
        Translated English string.
    """
    prompt = (
        f"Translate the following text to English. "
        f"Return only the translation, no explanations.\n\nText: {text}"
    )
    response = call_openrouter(api_key, _TRANSLATION_MODEL, prompt)
    return response["choices"][0]["message"]["content"]
