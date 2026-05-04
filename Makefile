.PHONY: test, check-style, format, test-all

help: ## Show this help message
	@echo "Dotfiles v2 - Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'


format:
	ruff format

test:
	poetry run python -m unittest discover -v tests

check-style:
	poetry run flake8 plugins --count --show-source --statistics
	poetry run flake8 tests --count --show-source --statistics

check-types:
	poetry run mypy .

test-all: test check-style