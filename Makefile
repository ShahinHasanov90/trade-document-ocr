.PHONY: install test serve lint clean

install:
	pip install -r requirements.txt
	pip install -e .

test:
	python -m pytest tests/ -v

serve:
	uvicorn src.ocr.api:app --host 0.0.0.0 --port 8000 --reload

lint:
	python -m flake8 src/ tests/ --max-line-length 120
	python -m mypy src/ocr/ --ignore-missing-imports

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/ dist/
