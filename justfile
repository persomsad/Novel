# Justfile for novel-agent project
# Install just: https://github.com/casey/just

# List all available commands
default:
    @just --list

# Run full checks (same as CI)
check:
    @echo "🔍 Running all checks..."
    poetry run black --check .
    poetry run ruff check .
    poetry run mypy .
    poetry run pytest --cov=src --cov-report=term
    @echo "✅ All checks passed!"

# Auto-fix formatting issues
fix:
    @echo "🔧 Auto-fixing issues..."
    poetry run black .
    poetry run ruff check --fix .
    @echo "✅ Fixed!"

# Quick check (before commit)
check-quick:
    @echo "🚀 Quick checks..."
    poetry run black --check .
    poetry run ruff check .

# Run tests only
test:
    poetry run pytest -v

# Run tests with coverage
test-cov:
    poetry run pytest --cov=src --cov-report=html --cov-report=term

# Install dependencies
install:
    poetry install

# Setup pre-commit hooks
setup-hooks:
    pre-commit install
    pre-commit install --hook-type pre-push
    @echo "✅ Git hooks installed!"

# Clean up build artifacts
clean:
    rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} +
    @echo "✅ Cleaned!"

# Run the CLI (for development)
run *ARGS:
    poetry run novel-agent {{ARGS}}
