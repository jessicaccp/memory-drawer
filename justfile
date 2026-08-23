default: check

# Run every check
check: lint format-check typecheck test

# Lint with ruff
lint:
    uv run ruff check .

# Format code in place
format:
    uv run ruff format .

# Verify formatting without changing files
format-check:
    uv run ruff format --check .

# Type check with mypy
typecheck:
    uv run mypy memory_drawer

# Run the tests
test:
    uv run pytest

# Run the CLI
run:
    uv run python -m memory_drawer
