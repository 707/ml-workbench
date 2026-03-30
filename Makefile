# ML Workbench — dev + deploy targets
# Primary deploy target: Render via the GitHub remote
#
# Usage:
#   make install        Install deps (creates .venv)
#   make run            Launch app locally
#   make lint           Run ruff checks
#   make typecheck      Run mypy on the main app modules
#   make test           Run full test suite with coverage
#   make check          Run lint + typecheck + tests
#   make deploy         Push to GitHub main (Render auto-deploys)
#   make deploy-hf      Push to Hugging Face Space via git

GITHUB_REMOTE ?= github
HF_SPACE ?= nad707/wb

.PHONY: install run lint typecheck test check deploy deploy-render deploy-hf verify-hf-space review-screenshots

REVIEW_BASE_URL ?= http://127.0.0.1:7860
REVIEW_OUTPUT_DIR ?=

install:
	uv sync --all-groups

run:
	uv run python app.py

lint:
	uv run ruff check .

typecheck:
	uv run mypy app.py charts.py token_tax.py token_tax_ui.py model_registry.py tokenizer.py corpora.py

test:
	uv run pytest -v --cov --cov-report=term-missing

check: lint typecheck test

deploy: deploy-render

deploy-render:
	@echo "Pushing repo root to GitHub for Render auto-deploy..."
	@git push $(GITHUB_REMOTE) main
	@echo "Done. Render should auto-deploy from the connected GitHub repo."

deploy-hf:
	@echo "Deploying repo root to HuggingFace Space..."
	@git push hf main
	@if [ -n "$$HF_TOKEN" ]; then \
		echo "Verifying Hugging Face runtime for $(HF_SPACE)..."; \
		UV_CACHE_DIR=$(pwd)/.uv-cache uv run python verify_hf_space.py --space "$(HF_SPACE)"; \
	else \
		echo "HF_TOKEN not set; skipping post-deploy runtime verification."; \
	fi
	@echo "Done. https://huggingface.co/spaces/$(HF_SPACE)"

verify-hf-space:
	@if [ -n "$$HF_TOKEN" ]; then \
		UV_CACHE_DIR=$(pwd)/.uv-cache uv run python verify_hf_space.py --space "$(HF_SPACE)"; \
	else \
		echo "HF_TOKEN not set; cannot verify runtime."; \
		exit 1; \
	fi

review-screenshots:
	@echo "Capturing screenshot review bundle from $(REVIEW_BASE_URL)..."
	@UV_CACHE_DIR=$(pwd)/.uv-cache uv run python scripts/capture_review_bundle.py --base-url "$(REVIEW_BASE_URL)" $(if $(REVIEW_OUTPUT_DIR),--output-dir "$(REVIEW_OUTPUT_DIR)",)
