# Reasoning Model Comparison — dev + deploy targets
# Requires: uv, huggingface-cli (installed via `make install`)
#
# Usage:
#   make install        Install deps (creates .venv)
#   make run            Launch app locally
#   make test           Run unit tests with coverage
#   make deploy         Upload to HF Spaces (set HF_SPACE=username/space-name)

HF_SPACE ?= ""

.PHONY: install run test deploy

install:
	uv sync --all-groups

run:
	uv run python app.py

test:
	uv run pytest test_app.py -v --cov=app --cov-report=term-missing

deploy:
	@if [ -z "$(HF_SPACE)" ]; then \
		echo "Error: set HF_SPACE=username/space-name"; \
		exit 1; \
	fi
	@echo "Deploying to https://huggingface.co/spaces/$(HF_SPACE)"
	@find . -type f \
		! -path "./.venv/*" \
		! -path "./.pytest_cache/*" \
		! -path "./__pycache__/*" \
		! -name "*.pyc" \
		! -name ".coverage" \
		! -name ".DS_Store" \
	| while read -r file; do \
		remote_path=$${file#./}; \
		uv run hf upload $(HF_SPACE) "$$remote_path" "$$remote_path" --repo-type space; \
	done
