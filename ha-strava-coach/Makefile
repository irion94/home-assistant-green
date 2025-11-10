.PHONY: help dev test lint format clean install

help:
	@echo "Available commands:"
	@echo "  make dev       - Install development dependencies"
	@echo "  make test      - Run test suite with coverage"
	@echo "  make lint      - Run linting checks (ruff + mypy)"
	@echo "  make format    - Format code with ruff"
	@echo "  make clean     - Remove build artifacts and cache"
	@echo "  make install   - Install package in development mode"

dev:
	pip install -e ".[dev,test]"
	pre-commit install

install:
	pip install -e .

test:
	pytest -q

lint:
	ruff check .
	mypy custom_components/strava_coach

format:
	ruff format .
	ruff check --fix .

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
