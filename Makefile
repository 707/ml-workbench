# ML Workbench — dev + deploy targets
# Requires: uv, git remote "hf" pointing at HF Space repo
#
# Usage:
#   make install        Install deps (creates .venv)
#   make run            Launch app locally
#   make test           Run full test suite with coverage
#   make deploy         Push to HF Spaces via git

HF_SPACE ?= nad707/llm-workbench

.PHONY: install run test deploy verify-space

install:
	uv sync --all-groups

run:
	uv run python app.py

test:
	uv run pytest -v --cov --cov-report=term-missing

deploy:
	@echo "Deploying repo root to HuggingFace Space..."
	@git push hf main
	@if [ -n "$$HF_TOKEN" ]; then \
		echo "Verifying Hugging Face runtime for $(HF_SPACE)..."; \
		UV_CACHE_DIR=$(pwd)/.uv-cache uv run python verify_hf_space.py --space "$(HF_SPACE)"; \
	else \
		echo "HF_TOKEN not set; skipping post-deploy runtime verification."; \
	fi
	@echo "Done. https://huggingface.co/spaces/$(HF_SPACE)"

verify-space:
	@if [ -n "$$HF_TOKEN" ]; then \
		UV_CACHE_DIR=$(pwd)/.uv-cache uv run python verify_hf_space.py --space "$(HF_SPACE)"; \
	else \
		echo "HF_TOKEN not set; cannot verify runtime."; \
		exit 1; \
	fi
