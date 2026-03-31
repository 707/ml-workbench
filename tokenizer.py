"""
Tokenizer Inspector module.

Provides tokenization utilities and a Gradio UI tab for inspecting how
different tokenizers handle input text.
"""

import gc
import html
import threading
from collections import OrderedDict
from time import perf_counter

import gradio as gr
from langdetect import LangDetectException, detect

from tokenizer_registry import supported_tokenizers_map

_AutoTokenizer = None
_snapshot_download = None


def _get_auto_tokenizer():
    global _AutoTokenizer
    if _AutoTokenizer is None:
        from transformers import AutoTokenizer
        _AutoTokenizer = AutoTokenizer
    return _AutoTokenizer


def _get_snapshot_download():
    global _snapshot_download
    if _snapshot_download is None:
        from huggingface_hub import snapshot_download
        _snapshot_download = snapshot_download
    return _snapshot_download


class _LazyAutoTokenizer:
    """Proxy that defers transformers import until first attribute access."""

    def __getattr__(self, name):
        return getattr(_get_auto_tokenizer(), name)


AutoTokenizer = _LazyAutoTokenizer()

SUPPORTED_TOKENIZERS: dict[str, str] = supported_tokenizers_map()


class TiktokenAdapter:
    """Wraps a tiktoken encoding to match the HuggingFace tokenizer interface.

    This allows tokenize_text(), fragmentation_ratio(), and other functions
    to work identically with tiktoken-based and HF-based tokenizers.
    """

    def __init__(self, encoding_name: str):
        import tiktoken
        self._enc = tiktoken.get_encoding(encoding_name)
        self._encoding_name = encoding_name

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        return self._enc.encode(text)

    def decode(self, token_ids: list[int]) -> str:
        return self._enc.decode(token_ids)

    def convert_ids_to_tokens(self, token_ids: list[int]) -> list[str]:
        return [self._enc.decode([tid]) for tid in token_ids]

    def __repr__(self) -> str:
        return f"TiktokenAdapter({self._encoding_name!r})"


# Module-level cache: name -> tokenizer object
_TOKENIZER_CACHE_MAX_SIZE = 2
_tokenizer_cache: OrderedDict[str, object] = OrderedDict()
_tokenizer_lock = threading.Lock()


def _local_snapshot_path(repo_id: str) -> str | None:
    """Return a cached local snapshot path when available, else None."""
    try:
        return _get_snapshot_download()(repo_id, local_files_only=True)
    except Exception:
        return None


def get_tokenizer(name: str):
    """Return (and cache) a tokenizer for the given registry name.

    Args:
        name: Key in SUPPORTED_TOKENIZERS (e.g. 'o200k_base', 'llama-3').

    Returns:
        A loaded tokenizer (AutoTokenizer or TiktokenAdapter).

    Raises:
        ValueError: If name is not in SUPPORTED_TOKENIZERS.
    """
    if name not in SUPPORTED_TOKENIZERS:
        raise ValueError(f"unknown tokenizer: '{name}'. Choose from {list(SUPPORTED_TOKENIZERS)}")

    with _tokenizer_lock:
        cached = _tokenizer_cache.get(name)
        if cached is not None:
            _tokenizer_cache.move_to_end(name)
            return cached

        if name not in _tokenizer_cache:
            repo_id = SUPPORTED_TOKENIZERS[name]
            if repo_id.startswith("tiktoken:"):
                encoding_name = repo_id.split(":", 1)[1]
                _tokenizer_cache[name] = TiktokenAdapter(encoding_name)
            else:
                try:
                    local_source = _local_snapshot_path(repo_id)
                    if local_source:
                        _tokenizer_cache[name] = AutoTokenizer.from_pretrained(
                            local_source,
                            local_files_only=True,
                        )
                    else:
                        _tokenizer_cache[name] = AutoTokenizer.from_pretrained(
                            repo_id,
                            local_files_only=True,
                        )
                except Exception:
                    try:
                        _tokenizer_cache[name] = AutoTokenizer.from_pretrained(repo_id)
                    except Exception as exc:
                        raise RuntimeError(
                            f"Failed to load tokenizer '{name}' from '{repo_id}'. "
                            f"Check your network connection or set TRANSFORMERS_OFFLINE=1 "
                            f"if you have a local cache. Original error: {exc}"
                        ) from exc
            _tokenizer_cache.move_to_end(name)
            while len(_tokenizer_cache) > _TOKENIZER_CACHE_MAX_SIZE:
                _tokenizer_cache.popitem(last=False)
                gc.collect()

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


def _is_non_space_delimited(text: str) -> bool:
    """Return True if the text is primarily CJK or Thai script.

    Uses a 30% threshold: if more than 30% of characters fall in CJK/Thai
    Unicode ranges, the text is treated as non-space-delimited.
    """
    if not text:
        return False
    cjk_thai_count = sum(1 for ch in text if (
        '\u4e00' <= ch <= '\u9fff' or   # CJK Unified Ideographs
        '\u3040' <= ch <= '\u309f' or   # Hiragana
        '\u30a0' <= ch <= '\u30ff' or   # Katakana
        '\uac00' <= ch <= '\ud7af' or   # Korean Hangul syllables
        '\u0e00' <= ch <= '\u0e7f'      # Thai
    ))
    return cjk_thai_count > len(text) * 0.3


def fragmentation_ratio(text: str, tokenizer) -> dict:
    """Compute the fragmentation ratio (tokens per unit) for text.

    For space-delimited scripts (Latin, Cyrillic, etc.) the unit is a
    whitespace-separated word.  For non-space-delimited scripts (CJK,
    Thai) the unit is a single character, since whitespace splitting
    produces meaningless "words".

    Args:
        text:      Input string.
        tokenizer: A loaded AutoTokenizer.

    Returns:
        Dict with:
          - 'ratio':       float tokens-per-unit (0.0 when text is empty)
          - 'token_count': int total token count
          - 'unit':        str "word" or "character" indicating what was counted
    """
    token_ids = tokenizer.encode(text)
    token_count = len(token_ids)

    if _is_non_space_delimited(text):
        unit_count = len(text)
        unit = "character"
    else:
        unit_count = len(text.split())
        unit = "word"

    ratio = token_count / unit_count if unit_count > 0 else 0.0
    return {"ratio": float(ratio), "token_count": token_count, "unit": unit}


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


# ---------------------------------------------------------------------------
# Token tax metrics (GH-3)
# ---------------------------------------------------------------------------


def relative_tokenization_cost(source_tokens: int, english_tokens: int | float) -> float:
    """Relative Tokenization Cost: source_tokens / english_tokens.

    Values > 1.0 indicate the source language pays a "token tax" vs English.
    Values < 1.0 indicate the source is more compact than English.

    Args:
        source_tokens:  Token count for the (possibly non-English) text.
        english_tokens: Token count for the English equivalent.

    Returns:
        Float ratio. Returns 1.0 when english_tokens is 0 (zero guard).
    """
    if english_tokens == 0:
        return 1.0
    return float(source_tokens) / float(english_tokens)


def byte_premium(text: str, english_text: str) -> float:
    """Ratio of UTF-8 byte length of text vs english_text.

    Values > 1.0 indicate the source text uses more bytes than English
    for equivalent content, reflecting script-level overhead.

    Args:
        text:         Source text.
        english_text: English equivalent text.

    Returns:
        Float ratio. Returns 1.0 when english_text is empty (zero guard).
    """
    source_bytes = len(text.encode("utf-8"))
    english_bytes = len(english_text.encode("utf-8"))
    if english_bytes == 0:
        return 1.0
    return float(source_bytes) / float(english_bytes)


def context_window_usage(token_count: int, window_size: int = 128_000) -> float:
    """Fraction of a context window consumed by a token count.

    Args:
        token_count: Number of tokens.
        window_size: Total context window size. Default 128k.

    Returns:
        Float between 0.0 and 1.0+. Returns 1.0 when window_size is 0.
    """
    if window_size == 0:
        return 1.0
    return float(token_count) / float(window_size)


def quality_risk_level(rtc: float) -> str:
    """Map a Relative Tokenization Cost to a quality risk band.

    Based on multilingual tokenization research (2025-2026):
    - low (<1.5): tokenizer handles this language well
    - moderate (1.5-2.5): noticeable token inflation
    - high (2.5-4.0): significant cost and potential quality impact
    - severe (>= 4.0): extreme fragmentation, likely quality degradation

    Args:
        rtc: Relative Tokenization Cost value.

    Returns:
        One of "low", "moderate", "high", "severe".
    """
    if rtc < 1.5:
        return "low"
    if rtc < 2.5:
        return "moderate"
    if rtc < 4.0:
        return "high"
    return "severe"


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

_NORMAL_BG_COLOURS = ("#e8f4f8", "#d4ecd4")


def _decode_via_convert_tokens(
    tokens: list[dict],
    token_ids: list[int],
    special_ids: set[int],
    hide_special_tokens: bool,
    tokenizer,
) -> list[str] | None:
    """Decode using tokenizer.convert_tokens_to_string. Returns None on failure."""
    tmp_chunks: list[str] = []
    visible_tokens: list[str] = []
    prev_decoded = ""
    for i, token_id in enumerate(token_ids):
        if hide_special_tokens and token_id in special_ids:
            tmp_chunks.append("")
            continue
        visible_tokens.append(str(tokens[i]["token"]))
        try:
            curr_decoded = tokenizer.convert_tokens_to_string(visible_tokens)
        except Exception:
            return None
        if not isinstance(curr_decoded, str):
            return None
        safe_prev = prev_decoded.replace("\ufffd", "")
        safe_curr = curr_decoded.replace("\ufffd", "")
        chunk = safe_curr[len(safe_prev):] if safe_curr.startswith(safe_prev) else ""
        tmp_chunks.append(chunk)
        prev_decoded = curr_decoded
    return tmp_chunks


def _decode_via_bytes(
    tokens: list[dict],
    token_ids: list[int],
    special_ids: set[int],
    hide_special_tokens: bool,
    byte_decoder: dict,
) -> list[str]:
    """Decode byte-level tokenizers (GPT-2/Llama-family) via raw byte accumulation."""
    chunks: list[str] = []
    buffer = bytearray()
    prev_decoded = ""
    for i, token_id in enumerate(token_ids):
        if hide_special_tokens and token_id in special_ids:
            chunks.append("")
            continue
        raw_token = str(tokens[i]["token"])
        for ch in raw_token:
            if ch in byte_decoder:
                buffer.append(int(byte_decoder[ch]))
            else:
                buffer.extend(ch.encode("utf-8", errors="ignore"))
        curr_decoded = bytes(buffer).decode("utf-8", errors="ignore")
        chunk = curr_decoded[len(prev_decoded):] if curr_decoded.startswith(prev_decoded) else ""
        chunks.append(chunk)
        prev_decoded = curr_decoded
    return chunks


def _decode_via_cumulative(
    tokens: list[dict],
    token_ids: list[int],
    special_ids: set[int],
    hide_special_tokens: bool,
    tokenizer,
) -> list[str]:
    """Generic fallback: cumulative tokenizer decode + prefix diff."""
    chunks: list[str] = []
    prev_decoded = ""
    for idx, token_id in enumerate(token_ids):
        if hide_special_tokens and token_id in special_ids:
            chunks.append("")
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
            try:
                chunk = tokenizer.decode(
                    [token_id],
                    skip_special_tokens=hide_special_tokens,
                    clean_up_tokenization_spaces=False,
                )
            except Exception:
                chunk = ""
        if "\ufffd" in chunk:
            chunk = chunk.replace("\ufffd", "")
        chunks.append(chunk)
        prev_decoded = curr_decoded
    return chunks


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
        if has_convert_tokens_to_string:
            result = _decode_via_convert_tokens(tokens, token_ids, special_ids, hide_special_tokens, tokenizer)
            if result is not None:
                display_chunks = result
                used_convert_path = True

        if not used_convert_path and isinstance(byte_decoder, dict) and byte_decoder:
            display_chunks = _decode_via_bytes(tokens, token_ids, special_ids, hide_special_tokens, byte_decoder)
        elif not used_convert_path:
            display_chunks = _decode_via_cumulative(tokens, token_ids, special_ids, hide_special_tokens, tokenizer)
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


def _handle_single(
    model_name: str,
    text: str,
    threshold: int,
    decoded_view: bool,
    english_text: str = "",
):
    """Handler logic for the Single tab — extracted for testability."""
    try:
        tok = get_tokenizer(model_name)
        tokens = tokenize_text(text, tok)
        token_count = len(tokens)
        oov = flag_oov_words(text, tok, threshold=int(threshold))
        token_html = render_tokens_html(
            tokens, oov, tokenizer=tok,
            decoded_view=decoded_view, hide_special_tokens=True,
        )
        frag = fragmentation_ratio(text, tok)
        lang = detect_language(text)

        ctx_usage = context_window_usage(token_count, 128_000)

        stats = (
            f"**Tokens:** {frag['token_count']}  \n"
            f"**Fragmentation ratio:** {frag['ratio']:.2f}  \n"
            f"**OOV words:** {len(oov)}  \n"
            f"**Detected language:** {lang}  \n"
            f"**Context usage (128k):** {ctx_usage:.4%}"
        )

        if lang == "en":
            stats += (
                "  \n**RTC vs English:** 1.0x  \n"
                "**Quality risk:** low"
            )
        elif english_text and english_text.strip():
            eng_tokens = tokenize_text(english_text.strip(), tok)
            rtc = relative_tokenization_cost(token_count, len(eng_tokens))
            risk = quality_risk_level(rtc)
            stats += (
                f"  \n**RTC vs English:** {rtc:.2f}x  \n"
                f"**Quality risk:** {risk}"
            )
        else:
            stats += (
                "  \n**RTC:** *(provide English equivalent for comparison)*"
            )

        return token_html, stats
    except Exception as exc:
        return "", f"Error: {exc}"


def _handle_compare(
    text: str,
    name_a: str,
    name_b: str,
    decoded_view: bool,
    english_text: str = "",
):
    """Handler logic for the Compare tab — extracted for testability."""
    try:
        tok_a = get_tokenizer(name_a)
        tok_b = get_tokenizer(name_b)
        tokens_a = tokenize_text(text, tok_a)
        tokens_b = tokenize_text(text, tok_b)
        count_a = len(tokens_a)
        count_b = len(tokens_b)
        html_a = render_tokens_html(
            tokens_a, set(), tokenizer=tok_a,
            decoded_view=decoded_view, hide_special_tokens=True,
        )
        html_b = render_tokens_html(
            tokens_b, set(), tokenizer=tok_b,
            decoded_view=decoded_view, hide_special_tokens=True,
        )
        frag_a = fragmentation_ratio(text, tok_a)
        frag_b = fragmentation_ratio(text, tok_b)
        ratio_md = (
            f"**{name_a}:** {frag_a['token_count']} tokens "
            f"(ratio {frag_a['ratio']:.2f})  \n"
            f"**{name_b}:** {frag_b['token_count']} tokens "
            f"(ratio {frag_b['ratio']:.2f})"
        )

        if english_text and english_text.strip():
            eng_tokens_a = tokenize_text(english_text.strip(), tok_a)
            eng_tokens_b = tokenize_text(english_text.strip(), tok_b)
            rtc_a = relative_tokenization_cost(count_a, len(eng_tokens_a))
            rtc_b = relative_tokenization_cost(count_b, len(eng_tokens_b))
            ratio_md += (
                f"  \n**{name_a} RTC:** {rtc_a:.2f}x  \n"
                f"**{name_b} RTC:** {rtc_b:.2f}x"
            )
            if rtc_a != rtc_b:
                better = name_a if rtc_a < rtc_b else name_b
                ratio_md += (
                    f"  \n*{better} is more efficient for this language.*"
                )

        return html_a, html_b, ratio_md
    except Exception as exc:
        return "", "", f"Error: {exc}"


def _runtime_status_markdown(title: str, lines: list[str]) -> str:
    """Render a compact runtime status panel."""
    return f"### {title}\n" + "\n".join(f"- {line}" for line in lines)


def _handle_single_with_status(
    model_name: str,
    text: str,
    threshold: int,
    decoded_view: bool,
    english_text: str = "",
    progress=gr.Progress(),
):
    """Return tokenization results with a stable runtime status summary."""
    progress(0.15, desc=f"Loading {model_name}")
    start = perf_counter()
    token_html, stats = _handle_single(model_name, text, threshold, decoded_view, english_text)
    duration = perf_counter() - start
    progress(1.0, desc="Tokenization complete")
    if stats.startswith("Error:"):
        status = _runtime_status_markdown(
            "Runtime Status",
            [
                f"Tokenization failed after **{duration:.1f}s**.",
                stats,
            ],
        )
    else:
        status = _runtime_status_markdown(
            "Runtime Status",
            [
                f"Tokenization completed in **{duration:.1f}s**.",
                f"Tokenizer: **{model_name}**.",
                f"Input length: **{len(text)}** characters.",
            ],
        )
    return token_html, stats, status


def _handle_compare_with_status(
    text: str,
    name_a: str,
    name_b: str,
    decoded_view: bool,
    english_text: str = "",
    progress=gr.Progress(),
):
    """Return tokenizer comparison results with a stable runtime status summary."""
    progress(0.15, desc=f"Comparing {name_a} vs {name_b}")
    start = perf_counter()
    html_a, html_b, ratio_md = _handle_compare(text, name_a, name_b, decoded_view, english_text)
    duration = perf_counter() - start
    progress(1.0, desc="Comparison complete")
    if ratio_md.startswith("Error:"):
        status = _runtime_status_markdown(
            "Runtime Status",
            [
                f"Comparison failed after **{duration:.1f}s**.",
                ratio_md,
            ],
        )
    else:
        status = _runtime_status_markdown(
            "Runtime Status",
            [
                f"Comparison completed in **{duration:.1f}s**.",
                f"Compared **{name_a}** vs **{name_b}**.",
                f"Input length: **{len(text)}** characters.",
            ],
        )
    return html_a, html_b, ratio_md, status


def build_tokenizer_ui() -> gr.Blocks:
    """Construct and return the Tokenizer Inspector Gradio Blocks UI.

    Returns:
        gr.Blocks instance with two inner tabs:
          - Single: inspect tokenization of one model.
          - Compare: side-by-side comparison of two models.
    """
    tokenizer_names = list(SUPPORTED_TOKENIZERS.keys())

    with gr.Blocks(title="Tokenizer Inspector") as demo:
        gr.Markdown(
            "## Tokenizer Inspector\n"
            "Explore how different tokenizers split text.\n\n"
            "Runtime note: tokenization runs inside the app and can take a few seconds on cold start. "
            "The status panel below each action reports progress and completion."
        )

        with gr.Tabs():
            # --- Single tab ---
            with gr.TabItem("Single"):
                with gr.Row():
                    single_model = gr.Dropdown(
                        choices=tokenizer_names,
                        value=tokenizer_names[0],
                        label="Tokenizer",
                        info="Tokenizer family to inspect on the current input text.",
                    )
                single_text = gr.Textbox(
                    label="Input Text",
                    placeholder="Type text to tokenize...",
                    lines=3,
                    elem_id="tokenizer-single-text",
                    info="Text that will be tokenized and visualized.",
                )
                oov_threshold = gr.Slider(
                    minimum=1, maximum=10, value=3, step=1,
                    label="OOV threshold (tokens per word)",
                    info="Words split into at least this many tokens are flagged as highly fragmented.",
                )
                single_english_text = gr.Textbox(
                    label="English Equivalent (optional)",
                    placeholder="Paste English translation for RTC comparison...",
                    lines=2,
                    elem_id="tokenizer-single-english-text",
                    info="Optional English equivalent used to compute RTC against the selected tokenizer.",
                )
                single_decoded_view = gr.Checkbox(
                    label="Readable token view (decode tokens, hide special tokens)",
                    value=False,
                    info="Show decoded token chunks instead of raw token pieces when possible.",
                )
                single_btn = gr.Button("Tokenize", variant="primary")
                single_status = gr.Markdown(
                    value=_runtime_status_markdown(
                        "Runtime Status",
                        ["Enter text and click **Tokenize** to inspect a tokenizer."],
                    )
                )
                single_html = gr.HTML(label="Token Visualisation")
                single_stats = gr.Markdown(label="Statistics")

                single_btn.click(
                    fn=_handle_single_with_status,
                    inputs=[single_model, single_text, oov_threshold, single_decoded_view, single_english_text],
                    outputs=[single_html, single_stats, single_status],
                )

            # --- Compare tab ---
            with gr.TabItem("Compare"):
                compare_text = gr.Textbox(
                    label="Input Text",
                    placeholder="Type text to compare tokenizers...",
                    lines=3,
                    elem_id="tokenizer-compare-text",
                    info="Shared text passed to both tokenizers for side-by-side comparison.",
                )
                with gr.Row():
                    cmp_model_a = gr.Dropdown(
                        choices=tokenizer_names,
                        value=tokenizer_names[0],
                        label="Tokenizer A",
                        info="First tokenizer family in the side-by-side comparison.",
                    )
                    cmp_model_b = gr.Dropdown(
                        choices=tokenizer_names,
                        value=tokenizer_names[1] if len(tokenizer_names) > 1 else tokenizer_names[0],
                        label="Tokenizer B",
                        info="Second tokenizer family in the side-by-side comparison.",
                    )
                compare_english_text = gr.Textbox(
                    label="English Equivalent (optional)",
                    placeholder="Paste English translation for RTC comparison...",
                    lines=2,
                    elem_id="tokenizer-compare-english-text",
                    info="Optional English equivalent used for RTC comparison in the compare view.",
                )
                compare_btn = gr.Button("Compare", variant="primary")
                with gr.Row():
                    cmp_html_a = gr.HTML(label="Tokenizer A")
                    cmp_html_b = gr.HTML(label="Tokenizer B")
                compare_decoded_view = gr.Checkbox(
                    label="Readable token view (decode tokens, hide special tokens)",
                    value=False,
                    info="Show readable decoded token chunks when comparing tokenizers.",
                )
                cmp_ratio_md = gr.Markdown(label="Comparison")
                compare_status = gr.Markdown(
                    value=_runtime_status_markdown(
                        "Runtime Status",
                        ["Enter shared text and click **Compare** to inspect two tokenizer families side by side."],
                    )
                )

                compare_btn.click(
                    fn=_handle_compare_with_status,
                    inputs=[compare_text, cmp_model_a, cmp_model_b, compare_decoded_view, compare_english_text],
                    outputs=[cmp_html_a, cmp_html_b, cmp_ratio_md, compare_status],
                )

    return demo
