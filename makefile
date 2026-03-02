.PHONY: install
install:
	@echo "🚀 INSTALLING ENVIRONMENT..."
	uv sync
	uv pip freeze > requirements.txt

.PHONY: run
run:
	@echo "🚀 RUNNING APP..."
	uv run streamlit run app.py