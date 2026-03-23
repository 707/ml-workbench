"""
Reasoning Model Comparison — Gradio app for HuggingFace Spaces.

Sends a question to DeepSeek-R1 and Llama-3.1-8B simultaneously via OpenRouter,
parses R1's <think> block, and displays a side-by-side comparison.
"""

import os
import requests
import gradio as gr
from collections import defaultdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Set OPENROUTER_API_KEY as a HF Space secret. When set, logged-in users
# run for free without entering their own key.
SERVER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

RATE_LIMIT = 10           # max requests per user
RATE_WINDOW = timedelta(hours=1)

# In-memory store: {username: [datetime, ...]}
_request_log: dict[str, list] = defaultdict(list)


def _check_rate_limit(username: str) -> bool:
    """Return True if the user is within the rate limit, False if exceeded."""
    now = datetime.utcnow()
    cutoff = now - RATE_WINDOW
    _request_log[username] = [t for t in _request_log[username] if t > cutoff]
    if len(_request_log[username]) >= RATE_LIMIT:
        return False
    _request_log[username].append(now)
    return True

# ---------------------------------------------------------------------------
# Model IDs
# ---------------------------------------------------------------------------

MODEL_R1 = "stepfun/step-3.5-flash"
MODEL_LLAMA = "meta-llama/llama-3.1-8b-instruct"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PRESET_QUESTIONS = [
    'How many r\'s are in "strawberry"?',
    "A bat and a ball cost $1.10. The bat costs $1 more than the ball. How much is the ball?",
    "Is 9677 a prime number?",
    "The Monty Hall problem: You pick door 1. Host opens door 3 (empty). Should you switch?",
    "If you fold a paper in half 42 times (paper = 0.1mm), how thick is it?",
]

# ---------------------------------------------------------------------------
# Phase 1: Core API Layer
# ---------------------------------------------------------------------------


def parse_think_block(text: str) -> tuple[str, str]:
    """Split R1 output into (reasoning, answer).

    Splits on the first </think> occurrence:
    - Everything before is reasoning (with leading <think> stripped).
    - Everything after is the answer (leading whitespace stripped).

    Returns ("", text) if no </think> tag is found.
    """
    if "</think>" not in text:
        return ("", text)

    before, after = text.split("</think>", 1)

    # Strip the opening <think> tag from the reasoning part
    if before.startswith("<think>"):
        before = before[len("<think>"):]

    reasoning = before
    answer = after.strip()

    return (reasoning, answer)


def call_openrouter(api_key: str, model: str, prompt: str) -> dict:
    """POST a chat completion request to OpenRouter.

    Args:
        api_key: OpenRouter API key.
        model:   Model ID string (e.g. "deepseek/deepseek-r1").
        prompt:  User question string.

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

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def extract_usage(response: dict) -> dict:
    """Extract token usage counts from an OpenRouter response.

    Returns a dict with keys:
      - prompt_tokens
      - completion_tokens
      - reasoning_tokens  (0 if not present — e.g. Llama responses)
    """
    usage = response.get("usage", {})
    details = usage.get("completion_tokens_details", {}) or {}

    reasoning_tokens = details.get("reasoning_tokens") or 0

    return {
        "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
        "completion_tokens": usage.get("completion_tokens", 0) or 0,
        "reasoning_tokens": reasoning_tokens,
    }


# ---------------------------------------------------------------------------
# Phase 2: Parallel Dispatch
# ---------------------------------------------------------------------------


def _call_r1(api_key: str, prompt: str) -> dict:
    """Call DeepSeek-R1 and return a result dict."""
    response = call_openrouter(api_key, MODEL_R1, prompt)
    content = response["choices"][0]["message"]["content"]
    reasoning, answer = parse_think_block(content)
    return {
        "reasoning": reasoning,
        "answer": answer,
        "usage": extract_usage(response),
    }


def _call_llama(api_key: str, prompt: str) -> dict:
    """Call Llama-3.1-8B and return a result dict."""
    response = call_openrouter(api_key, MODEL_LLAMA, prompt)
    content = response["choices"][0]["message"]["content"]
    return {
        "answer": content,
        "usage": extract_usage(response),
    }


def run_comparison(api_key: str, question: str) -> tuple[dict, dict]:
    """Run both models concurrently and return (r1_result, llama_result).

    Each result is an independent dict. If one model fails, the other
    result is still returned — the failed model gets {"error": str}.
    """
    r1_result: dict = {}
    llama_result: dict = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_call_r1, api_key, question): "r1",
            executor.submit(_call_llama, api_key, question): "llama",
        }

        for future in as_completed(futures):
            label = futures[future]
            try:
                result = future.result()
                if label == "r1":
                    r1_result = result
                else:
                    llama_result = result
            except Exception as exc:
                error_dict = {"error": str(exc)}
                if label == "r1":
                    r1_result = error_dict
                else:
                    llama_result = error_dict

    return r1_result, llama_result


# ---------------------------------------------------------------------------
# Phase 3: Gradio UI
# ---------------------------------------------------------------------------


def _format_usage(usage: dict) -> str:
    """Render token usage as a Markdown string."""
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    reasoning = usage.get("reasoning_tokens", 0)
    answer_tokens = completion - reasoning if reasoning else completion

    lines = [
        f"**Prompt tokens:** {prompt}",
        f"**Completion tokens:** {completion}",
    ]
    if reasoning:
        lines.append(f"**Reasoning tokens:** {reasoning}")
        lines.append(f"**Answer tokens:** {answer_tokens}")

    return "  \n".join(lines)


def compare(api_key: str, preset: str, custom: str):
    """Gradio handler: pick question, call run_comparison, format outputs."""
    question = custom.strip() if custom.strip() else preset

    if not api_key.strip():
        return "", "No API key provided.", "", "No API key provided.", ""
    if not question:
        return "", "No question provided.", "", "No question provided.", ""

    r1_result, llama_result = run_comparison(api_key.strip(), question)

    # R1 outputs
    if "error" in r1_result:
        r1_reasoning = ""
        r1_answer = f"Error: {r1_result['error']}"
        r1_stats = ""
    else:
        r1_reasoning = r1_result.get("reasoning", "")
        r1_answer = r1_result.get("answer", "")
        r1_stats = _format_usage(r1_result.get("usage", {}))

    # Llama outputs
    if "error" in llama_result:
        llama_answer = f"Error: {llama_result['error']}"
        llama_stats = ""
    else:
        llama_answer = llama_result.get("answer", "")
        llama_stats = _format_usage(llama_result.get("usage", {}))

    return r1_reasoning, r1_answer, r1_stats, llama_answer, llama_stats


def build_ui() -> gr.Blocks:
    """Construct and return the Gradio Blocks UI."""
    with gr.Blocks(title="Reasoning Model Comparison") as demo:
        gr.Markdown("# Reasoning Model Comparison\nStep 3.5 Flash vs Llama-3.1-8B via OpenRouter")

        # Auth row — HF login button + status message
        with gr.Row():
            gr.LoginButton()
        auth_msg = gr.Markdown(
            "**Login with HuggingFace** to run for free using the shared key.  \n"
            "Or enter your own [OpenRouter](https://openrouter.ai) key below "
            "— free tier, no credit card required."
        )

        # API key input — hidden when user is logged in and server key is available
        with gr.Row() as key_row:
            api_key = gr.Textbox(
                label="OpenRouter API Key",
                type="password",
                placeholder="sk-or-... — get a free key at openrouter.ai",
                value=SERVER_KEY,
            )

        with gr.Row():
            preset = gr.Radio(
                choices=PRESET_QUESTIONS,
                label="Preset Questions",
                value=PRESET_QUESTIONS[0],
            )

        with gr.Row():
            custom = gr.Textbox(
                label="Custom Question (overrides preset if filled)",
                placeholder="Type your own question here...",
            )

        submit_btn = gr.Button("Compare →", variant="primary")

        with gr.Row():
            with gr.Column():
                gr.Markdown("## Step 3.5 Flash (Reasoning)")
                r1_reasoning = gr.Textbox(
                    label="Reasoning Trace",
                    lines=10,
                    max_lines=30,
                    interactive=False,
                )
                r1_answer = gr.Textbox(
                    label="Final Answer",
                    lines=4,
                    interactive=False,
                )
                r1_stats = gr.Markdown()

            with gr.Column():
                gr.Markdown("## Llama-3.1-8B")
                llama_answer = gr.Textbox(
                    label="Response",
                    lines=10,
                    max_lines=30,
                    interactive=False,
                )
                llama_stats = gr.Markdown()

        # Update auth message and key visibility when login state changes
        def _on_load(profile: gr.OAuthProfile | None):
            if profile and SERVER_KEY:
                return (
                    gr.update(value=f"Logged in as **{profile.name}** — running on shared key, no setup needed."),
                    gr.update(visible=False),
                )
            elif profile:
                return (
                    gr.update(value=f"Logged in as **{profile.name}** — enter your OpenRouter key below."),
                    gr.update(visible=True),
                )
            return gr.update(), gr.update()

        demo.load(_on_load, inputs=None, outputs=[auth_msg, key_row])

        # Use server key when user is logged in and it's available
        def _compare(
            api_key_val: str,
            preset_val: str,
            custom_val: str,
            profile: gr.OAuthProfile | None,
            oauth_token: gr.OAuthToken | None,
        ):
            using_server_key = oauth_token is not None and bool(SERVER_KEY)

            if using_server_key:
                if profile is None:
                    blocked = ("", "Login with HuggingFace to use the shared key.", "", "", "")
                    return blocked
                if not _check_rate_limit(profile.username):
                    blocked = ("", f"Rate limit reached ({RATE_LIMIT} requests/hour). Try again later.", "", "", "")
                    return blocked

            effective_key = SERVER_KEY if using_server_key else api_key_val
            return compare(effective_key, preset_val, custom_val)

        submit_btn.click(
            fn=_compare,
            inputs=[api_key, preset, custom],
            outputs=[r1_reasoning, r1_answer, r1_stats, llama_answer, llama_stats],
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = build_ui()
    app.queue(max_size=5).launch()
