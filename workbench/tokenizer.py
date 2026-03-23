"""
Tokenizer Inspector module.

Provides tokenization utilities and a Gradio UI tab for inspecting how
different tokenizers handle input text.
"""

import html
import gradio as gr
from transformers import AutoTokenizer
from langdetect import detect, LangDetectException

from openrouter import call_openrouter

# ---------------------------------------------------------------------------
# Tokenizer registry
# ---------------------------------------------------------------------------

SUPPORTED_TOKENIZERS: dict[str, str] = {
    "gpt2": "gpt2",
    "llama-3": "NousResearch/Meta-Llama-3-8B",
    "mistral": "mistralai/Mistral-7B-v0.1",
}

# Module-level cache: name -> tokenizer object
_tokenizer_cache: dict[str, object] = {}


def get_tokenizer(name: str):
    """Return (and cache) a tokenizer for the given registry name.

    Args:
        name: Key in SUPPORTED_TOKENIZERS (e.g. 'gpt2', 'llama-3', 'mistral').

    Returns:
        A loaded AutoTokenizer instance.

    Raises:
        ValueError: If name is not in SUPPORTED_TOKENIZERS.
    """
    if name not in SUPPORTED_TOKENIZERS:
        raise ValueError(f"unknown tokenizer: '{name}'. Choose from {list(SUPPORTED_TOKENIZERS)}")

    if name not in _tokenizer_cache:
        repo_id = SUPPORTED_TOKENIZERS[name]
        _tokenizer_cache[name] = AutoTokenizer.from_pretrained(repo_id)

    return _tokenizer_cache[name]


# ---------------------------------------------------------------------------
# Core tokenization helpers
# ---------------------------------------------------------------------------


def tokenize_text(text: str, tokenizer) -> list[dict]:
    """Tokenize text and return a list of {token, id} dicts.

    Args:
        text:      Input string to tokenize.
        tokenizer: A loaded AutoTokenizer (or compatible mock).

    Returns:
        List of dicts with keys 'token' (str) and 'id' (int).
    """
    token_ids = tokenizer.encode(text)
    tokens = tokenizer.convert_ids_to_tokens(token_ids)
    return [{"token": str(tok), "id": int(tid)} for tok, tid in zip(tokens, token_ids)]


def fragmentation_ratio(text: str, tokenizer) -> dict[str, float]:
    """Compute the fragmentation ratio (tokens per word) for text.

    Args:
        text:      Input string.
        tokenizer: A loaded AutoTokenizer.

    Returns:
        Dict with:
          - 'ratio': float tokens-per-word (0.0 when text is empty)
          - 'token_count': int total token count
    """
    token_ids = tokenizer.encode(text)
    token_count = len(token_ids)
    words = text.split()
    word_count = len(words)
    ratio = token_count / word_count if word_count > 0 else 0.0
    return {"ratio": float(ratio), "token_count": token_count}


def flag_oov_words(text: str, tokenizer, threshold: int = 3) -> set[str]:
    """Return the set of words that fragment into >= threshold tokens.

    A word is considered out-of-vocabulary (OOV) relative to a tokenizer when
    the tokenizer splits it into many sub-word pieces.

    Args:
        text:      Input string.
        tokenizer: A loaded AutoTokenizer.
        threshold: Minimum token count (inclusive) to flag a word. Default 3.

    Returns:
        Set of words that meet or exceed the threshold.
    """
    oov: set[str] = set()
    for word in text.split():
        ids = tokenizer.encode(word, add_special_tokens=False)
        if len(ids) >= threshold:
            oov.add(word)
    return oov


# ---------------------------------------------------------------------------
# Language helpers
# ---------------------------------------------------------------------------


def detect_language(text: str) -> str:
    """Detect the language of text.

    Wraps langdetect.detect. Returns 'en' on LangDetectException.

    Args:
        text: Input string.

    Returns:
        BCP-47 language code string, e.g. 'en', 'fr', 'de'.
    """
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def efficiency_score(input_tokens: int, english_tokens: int) -> float:
    """Compute tokenization efficiency relative to an English translation.

    Score = english_tokens / input_tokens. Values > 1.0 indicate the source
    language is more compact than English for this tokenizer; < 1.0 means
    more tokens are needed.

    Args:
        input_tokens:   Token count for the original (possibly non-English) text.
        english_tokens: Token count for the English translation.

    Returns:
        Float ratio. Returns 1.0 when english_tokens is 0 or input_tokens is 0.
    """
    if english_tokens == 0 or input_tokens == 0:
        return 1.0
    return float(english_tokens) / float(input_tokens)


def translate_to_english(text: str, api_key: str) -> str:
    """Translate text to English using OpenRouter.

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
    response = call_openrouter(api_key, "meta-llama/llama-3.1-8b-instruct", prompt)
    return response["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

_NORMAL_BG_COLOURS = ("#e8f4f8", "#d4ecd4")


def render_tokens_html(tokens: list[dict], oov_words: set[str]) -> str:
    """Render a list of tokens as coloured HTML spans.

    Normal tokens alternate between two background colours. OOV tokens are
    highlighted with #ffcccc. All token text is HTML-escaped.

    Args:
        tokens:    List of {'token': str, 'id': int} dicts.
        oov_words: Set of OOV word strings to highlight.

    Returns:
        HTML string containing one <span> per token.
    """
    parts: list[str] = []
    for i, entry in enumerate(tokens):
        token_text = html.escape(entry["token"])
        if entry["token"] in oov_words:
            bg = "#ffcccc"
        else:
            bg = _NORMAL_BG_COLOURS[i % 2]
        parts.append(
            f'<span style="background:{bg};padding:2px 4px;border-radius:3px;'
            f'margin:1px;display:inline-block;" title="id:{entry["id"]}">'
            f"{token_text}</span>"
        )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------


def build_tokenizer_ui() -> gr.Blocks:
    """Construct and return the Tokenizer Inspector Gradio Blocks UI.

    Returns:
        gr.Blocks instance with two inner tabs:
          - Single: inspect tokenization of one model.
          - Compare: side-by-side comparison of two models.
    """
    tokenizer_names = list(SUPPORTED_TOKENIZERS.keys())

    with gr.Blocks(title="Tokenizer Inspector") as demo:
        gr.Markdown("## Tokenizer Inspector\nExplore how different tokenizers split text.")

        with gr.Tabs():
            # --- Single tab ---
            with gr.TabItem("Single"):
                with gr.Row():
                    single_model = gr.Dropdown(
                        choices=tokenizer_names,
                        value=tokenizer_names[0],
                        label="Tokenizer",
                    )
                single_text = gr.Textbox(
                    label="Input Text",
                    placeholder="Type text to tokenize...",
                    lines=3,
                )
                oov_threshold = gr.Slider(
                    minimum=1, maximum=10, value=3, step=1,
                    label="OOV threshold (tokens per word)",
                )
                single_btn = gr.Button("Tokenize", variant="primary")
                single_html = gr.HTML(label="Token Visualisation")
                single_stats = gr.Markdown(label="Statistics")

                def _run_single(model_name: str, text: str, threshold: int):
                    try:
                        tok = get_tokenizer(model_name)
                        tokens = tokenize_text(text, tok)
                        oov = flag_oov_words(text, tok, threshold=int(threshold))
                        token_html = render_tokens_html(tokens, oov)
                        frag = fragmentation_ratio(text, tok)
                        lang = detect_language(text)
                        stats = (
                            f"**Tokens:** {frag['token_count']}  \n"
                            f"**Fragmentation ratio:** {frag['ratio']:.2f}  \n"
                            f"**OOV words:** {len(oov)}  \n"
                            f"**Detected language:** {lang}"
                        )
                        return token_html, stats
                    except Exception as exc:
                        return "", f"Error: {exc}"

                single_btn.click(
                    fn=_run_single,
                    inputs=[single_model, single_text, oov_threshold],
                    outputs=[single_html, single_stats],
                )

            # --- Compare tab ---
            with gr.TabItem("Compare"):
                compare_text = gr.Textbox(
                    label="Input Text",
                    placeholder="Type text to compare tokenizers...",
                    lines=3,
                )
                with gr.Row():
                    cmp_model_a = gr.Dropdown(
                        choices=tokenizer_names,
                        value=tokenizer_names[0],
                        label="Tokenizer A",
                    )
                    cmp_model_b = gr.Dropdown(
                        choices=tokenizer_names,
                        value=tokenizer_names[1] if len(tokenizer_names) > 1 else tokenizer_names[0],
                        label="Tokenizer B",
                    )
                compare_btn = gr.Button("Compare", variant="primary")
                with gr.Row():
                    cmp_html_a = gr.HTML(label="Tokenizer A")
                    cmp_html_b = gr.HTML(label="Tokenizer B")
                cmp_ratio_md = gr.Markdown(label="Comparison")

                def _run_compare(text: str, name_a: str, name_b: str):
                    try:
                        tok_a = get_tokenizer(name_a)
                        tok_b = get_tokenizer(name_b)
                        tokens_a = tokenize_text(text, tok_a)
                        tokens_b = tokenize_text(text, tok_b)
                        html_a = render_tokens_html(tokens_a, set())
                        html_b = render_tokens_html(tokens_b, set())
                        frag_a = fragmentation_ratio(text, tok_a)
                        frag_b = fragmentation_ratio(text, tok_b)
                        ratio_md = (
                            f"**{name_a}:** {frag_a['token_count']} tokens "
                            f"(ratio {frag_a['ratio']:.2f})  \n"
                            f"**{name_b}:** {frag_b['token_count']} tokens "
                            f"(ratio {frag_b['ratio']:.2f})"
                        )
                        return html_a, html_b, ratio_md
                    except Exception as exc:
                        return "", "", f"Error: {exc}"

                compare_btn.click(
                    fn=_run_compare,
                    inputs=[compare_text, cmp_model_a, cmp_model_b],
                    outputs=[cmp_html_a, cmp_html_b, cmp_ratio_md],
                )

    return demo
