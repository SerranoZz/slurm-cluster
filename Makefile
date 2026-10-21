PY ?= .venv/bin

lint:
	$(PY)/yamllint .
	cd ansible && ../$(PY)/ansible-lint

test:
	$(PY)/pytest tests/

.PHONY: lint test
