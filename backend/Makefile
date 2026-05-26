.PHONY: install dev test lint format clean

VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

install: $(VENV)/bin/activate

dev: install
	$(PYTHON) -m uvicorn main:app --reload --port 8000

test: install
	$(PYTHON) -m pytest tests/ -v

lint: install
	$(PYTHON) -m ruff check .

format: install
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

clean:
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf $(VENV)
