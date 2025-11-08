# Justfile for novel-agent project
# Install just: https://github.com/casey/just

# List all available commands
default:
    @just --list

# Run full checks (EXACTLY same as CI - run before push!)
check:
    @echo "🔍 Running CI checks locally..."
    @echo ""
    @echo "1️⃣  Black (format check)..."
    poetry run black --check .
    @echo ""
    @echo "2️⃣  Ruff (lint)..."
    poetry run ruff check .
    @echo ""
    @echo "3️⃣  Mypy (type check)..."
    poetry run mypy .
    @echo ""
    @echo "4️⃣  Pytest (tests + coverage)..."
    poetry run pytest --cov=src --cov-report=term
    @echo ""
    @echo "✅ All CI checks passed! Safe to push."

# Auto-fix formatting issues
fix:
    @echo "🔧 Auto-fixing issues..."
    poetry run black .
    poetry run ruff check --fix .
    @echo "✅ Fixed!"

# Quick check (before commit - fast!)
check-quick:
    @echo "🚀 Quick checks (format + lint)..."
    poetry run black --check .
    poetry run ruff check .
    @echo "✅ Quick checks passed!"

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
