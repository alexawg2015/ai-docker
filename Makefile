.PHONY: install run test clean

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r app/requirements.txt pytest pytest-asyncio
	@test -f .env || cp .env.example .env
	@echo ""
	@echo "Edit .env and add OPENROUTER_API_KEY, then: make run"

run:
	$(VENV)/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	$(VENV)/bin/pytest -q

clean:
	rm -rf $(VENV) __pycache__ */__pycache__ .pytest_cache
