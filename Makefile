PYTHON ?= uv run python

.PHONY: run

run:
	uv run main.py $(ARGS)
