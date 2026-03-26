# ML Workbench — dev + deploy targets
# Requires: uv, git remote "hf" pointing at HF Space repo
#
# Usage:
#   make install        Install deps (creates .venv)
#   make run            Launch app locally
#   make test           Run full test suite with coverage
#   make deploy         Push to HF Spaces via git

.PHONY: install run test deploy

install:
	uv sync --all-groups

run:
	uv run python app.py

test:
	uv run pytest -v --cov --cov-report=term-missing

deploy:
	@echo "Deploying workbench/ to HuggingFace Space..."
	@cd .. && git subtree push --prefix workbench hf main \
		|| (echo "\nSubtree push rejected — force-pushing..." \
		    && git subtree split --prefix workbench -b _hf_deploy \
		    && git push hf _hf_deploy:main --force \
		    && git branch -D _hf_deploy)
	@echo "Done. https://huggingface.co/spaces/nad707/workbench"
