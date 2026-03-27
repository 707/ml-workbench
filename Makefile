# ML Workbench — dev + deploy targets
# Primary deploy target: Render via the GitHub remote
#
# Usage:
#   make install        Install deps (creates .venv)
#   make run            Launch app locally
#   make test           Run full test suite with coverage
#   make deploy         Push to GitHub main (Render auto-deploys)
#   make deploy-hf      Push to Hugging Face Space via git

GITHUB_REMOTE ?= github
HF_SPACE ?= nad707/wb

.PHONY: install run test deploy deploy-render deploy-hf verify-hf-space

install:
	uv sync --all-groups

run:
	uv run python app.py

test:
	uv run pytest -v --cov --cov-report=term-missing

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
