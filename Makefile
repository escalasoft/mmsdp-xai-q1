.PHONY: help install-dev test lint format-check tree clean

PYTHON ?= python3

help:
	@printf '%s\n' 'Available targets: help install-dev test lint format-check tree clean'

install-dev:
	$(PYTHON) -m pip install -r requirements/dev.txt

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check src tests

format-check:
	$(PYTHON) -m ruff format --check src tests

tree:
	find . -path './.git' -prune -o -print | sort

clean:
	find . -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.ruff_cache' \) -prune -exec rm -rf {} +
