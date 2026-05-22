.PHONY: build test typecheck clean

build:
	poetry install

test:
	poetry run pytest

typecheck:
	poetry run mypy aw_watcher_screenshot --ignore-missing-imports

clean:
	rm -rf build dist
	rm -rf aw_watcher_screenshot/__pycache__ tests/__pycache__
