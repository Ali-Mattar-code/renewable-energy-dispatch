.PHONY: install reproduce test lint api dashboard

install:
	python -m pip install -e ".[dev,app]"

reproduce:
	hybrid-dispatch reproduce --config configs/reference.json

test:
	python -m pytest

lint:
	python -m ruff check .

api:
	uvicorn hybrid_dispatch.api:app --reload

dashboard:
	streamlit run app/dashboard.py
