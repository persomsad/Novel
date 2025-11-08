# Justfile for novel-agent project
# Install just: https://github.com/casey/just
#
# 注意：大部分检查已由 pre-commit hooks 自动化
#   - git commit → 自动格式化 + lint + 类型检查
#   - git push   → 自动运行测试
#
# 本文件主要用于：
#   1. 手动触发完整CI检查（验证PR前）
#   2. 开发调试（单独运行测试、清理等）

# List all available commands
default:
    @just --list

# Verify pre-commit hooks are installed
check-hooks:
    #!/usr/bin/env bash
    if [ ! -f .git/hooks/pre-commit ]; then
        echo "❌ Pre-commit hooks not installed!"
        echo "Run: just setup-hooks"
        exit 1
    fi
    echo "✅ Pre-commit hooks installed"

# Run FULL CI checks manually (same as GitHub Actions)
ci:
    @echo "🔍 Running FULL CI checks (same as GitHub Actions)..."
    @echo ""
    poetry run black --check .
    poetry run ruff check .
    poetry run mypy .
    poetry run pytest --cov=src --cov-report=term
    @echo ""
    @echo "✅ All CI checks passed!"

# Run tests (for development/debugging)
test *ARGS:
    poetry run pytest {{ARGS}}

# Run tests with HTML coverage report
test-cov:
    poetry run pytest --cov=src --cov-report=html --cov-report=term
    @echo "📊 Coverage report: htmlcov/index.html"

# Install dependencies + setup hooks (one-time setup)
setup:
    poetry install --extras dev
    pre-commit install
    pre-commit install --hook-type pre-push
    @echo "✅ Setup complete!"

# Clean up build artifacts
clean:
    rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    @echo "✅ Cleaned!"

# Run the CLI (for development)
dev *ARGS:
    poetry run novel-agent {{ARGS}}
