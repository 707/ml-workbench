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


def render_tokens_html(
    tokens: list[dict],
    oov_words: set[str],
    tokenizer=None,
    decoded_view: bool = False,
    hide_special_tokens: bool = True,
) -> str:
    """Render a list of tokens as coloured HTML spans.

    Normal tokens alternate between two background colours. OOV tokens are
    highlighted with #ffcccc. All token text is HTML-escaped.

    When decoded_view=True, token IDs are decoded back into readable text
    snippets. Special tokens (e.g. BOS) are hidden by default in this mode.
    """
    special_ids = set(getattr(tokenizer, "all_special_ids", [])) if tokenizer else set()
    parts: list[str] = []
    display_chunks: list[str] = []
    token_ids = [int(entry["id"]) for entry in tokens]
    byte_decoder = getattr(tokenizer, "byte_decoder", None) if tokenizer else None
    has_convert_tokens_to_string = bool(tokenizer and hasattr(tokenizer, "convert_tokens_to_string"))

    if decoded_view and tokenizer is not None:
        used_convert_path = False
        # Prefer tokenizer-native token-string reconstruction when available.
        # This handles byte-level tokenizers more reliably than per-token decode.
        if has_convert_tokens_to_string:
            tmp_chunks: list[str] = []
            visible_tokens: list[str] = []
            prev_decoded = ""
            convert_path_ok = True
            for i, token_id in enumerate(token_ids):
                if hide_special_tokens and token_id in special_ids:
                    tmp_chunks.append("")
                    continue
                visible_tokens.append(str(tokens[i]["token"]))
                try:
                    curr_decoded = tokenizer.convert_tokens_to_string(visible_tokens)
                except Exception:
                    convert_path_ok = False
                    break
                if not isinstance(curr_decoded, str):
                    convert_path_ok = False
                    break
                safe_prev = prev_decoded.replace("\ufffd", "")
                safe_curr = curr_decoded.replace("\ufffd", "")
                chunk = safe_curr[len(safe_prev):] if safe_curr.startswith(safe_prev) else ""
                tmp_chunks.append(chunk)
                prev_decoded = curr_decoded
            if convert_path_ok:
                display_chunks = tmp_chunks
                used_convert_path = True

        # For byte-level tokenizers (GPT-2/Llama-family), decode via raw byte
        # accumulation to avoid replacement-character noise in multibyte scripts.
        if not used_convert_path and isinstance(byte_decoder, dict) and byte_decoder:
            buffer = bytearray()
            prev_decoded = ""
            for i, token_id in enumerate(token_ids):
                if hide_special_tokens and token_id in special_ids:
                    display_chunks.append("")
                    continue

                raw_token = str(tokens[i]["token"])
                for ch in raw_token:
                    if ch in byte_decoder:
                        buffer.append(int(byte_decoder[ch]))
                    else:
                        buffer.extend(ch.encode("utf-8", errors="ignore"))

                curr_decoded = bytes(buffer).decode("utf-8", errors="ignore")
                chunk = curr_decoded[len(prev_decoded):] if curr_decoded.startswith(prev_decoded) else ""
                display_chunks.append(chunk)
                prev_decoded = curr_decoded
        elif not used_convert_path:
            # Generic fallback: cumulative tokenizer decode + prefix diff.
            prev_decoded = ""
            for idx, token_id in enumerate(token_ids):
                if hide_special_tokens and token_id in special_ids:
                    display_chunks.append("")
                    continue
                try:
                    curr_decoded = tokenizer.decode(
                        token_ids[: idx + 1],
                        skip_special_tokens=hide_special_tokens,
                        clean_up_tokenization_spaces=False,
                    )
                except Exception:
                    curr_decoded = prev_decoded

                if curr_decoded.startswith(prev_decoded):
                    chunk = curr_decoded[len(prev_decoded):]
                else:
                    # Conservative fallback if tokenizer decode is non-prefix-stable.
                    try:
                        chunk = tokenizer.decode(
                            [token_id],
                            skip_special_tokens=hide_special_tokens,
                            clean_up_tokenization_spaces=False,
                        )
                    except Exception:
                        chunk = ""
                # Strip replacement chars in readable mode.
                if "\ufffd" in chunk:
                    chunk = chunk.replace("\ufffd", "")
                display_chunks.append(chunk)
                prev_decoded = curr_decoded
    else:
        display_chunks = [str(entry["token"]) for entry in tokens]

    for i, entry in enumerate(tokens):
        raw_token = str(entry["token"])
        token_id = int(entry["id"])
        token_text_for_display = display_chunks[i]

        if decoded_view and tokenizer is not None:
            if not token_text_for_display and hide_special_tokens:
                continue

        token_text = html.escape(token_text_for_display)
        if raw_token in oov_words:
            bg = "#ffcccc"
        else:
            bg = _NORMAL_BG_COLOURS[i % 2]
        title = f"id:{token_id}" if decoded_view else f"id:{token_id} | raw:{html.escape(raw_token)}"
        parts.append(
            f'<span style="background:{bg};padding:2px 4px;border-radius:3px;'
            f'margin:1px;display:inline-block;white-space:pre;color:#000;" title="{title}">'
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
                single_decoded_view = gr.Checkbox(
                    label="Readable token view (decode tokens, hide special tokens)",
                    value=False,
                )
                single_btn = gr.Button("Tokenize", variant="primary")
                single_html = gr.HTML(label="Token Visualisation")
                single_stats = gr.Markdown(label="Statistics")

                def _run_single(model_name: str, text: str, threshold: int, decoded_view: bool):
                    try:
                        tok = get_tokenizer(model_name)
                        tokens = tokenize_text(text, tok)
                        oov = flag_oov_words(text, tok, threshold=int(threshold))
                        token_html = render_tokens_html(
                            tokens,
                            oov,
                            tokenizer=tok,
                            decoded_view=decoded_view,
                            hide_special_tokens=True,
                        )
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
                    inputs=[single_model, single_text, oov_threshold, single_decoded_view],
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
                compare_decoded_view = gr.Checkbox(
                    label="Readable token view (decode tokens, hide special tokens)",
                    value=False,
                )
                cmp_ratio_md = gr.Markdown(label="Comparison")

                def _run_compare(text: str, name_a: str, name_b: str, decoded_view: bool):
                    try:
                        tok_a = get_tokenizer(name_a)
                        tok_b = get_tokenizer(name_b)
                        tokens_a = tokenize_text(text, tok_a)
                        tokens_b = tokenize_text(text, tok_b)
                        html_a = render_tokens_html(
                            tokens_a,
                            set(),
                            tokenizer=tok_a,
                            decoded_view=decoded_view,
                            hide_special_tokens=True,
                        )
                        html_b = render_tokens_html(
                            tokens_b,
                            set(),
                            tokenizer=tok_b,
                            decoded_view=decoded_view,
                            hide_special_tokens=True,
                        )
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
                    inputs=[compare_text, cmp_model_a, cmp_model_b, compare_decoded_view],
                    outputs=[cmp_html_a, cmp_html_b, cmp_ratio_md],
                )

    return demo
