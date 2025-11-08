# 开发指南

## 🚀 自动化工作流

**好消息**：大部分检查已经自动化了！

- `git commit` → 自动格式化 + lint + 类型检查（pre-commit hooks）
- `git push` → 自动运行所有测试（pre-push hooks）

**你只需正常开发，git hooks会自动保证代码质量！**

## Just命令（开发调试）

### 完整CI检查（验证PR前）

```bash
just ci
```

手动运行完整CI检查（与GitHub Actions相同）。**通常不需要运行，因为git hooks已自动检查。**

### 运行测试

```bash
just test              # 运行所有测试
just test tests/test_cli.py  # 运行特定测试
just test-cov          # 生成HTML覆盖率报告
```

### 一键setup（克隆项目后）

```bash
just setup
```

安装依赖 + 配置git hooks，一步到位。

## Git Workflow

### 1. 开始新Issue

```bash
# 确保在main分支且是最新的
git checkout main
git pull

# 创建feature分支
git checkout -b feat/4-issue-description

# 开始开发...
```

### 2. 提交代码（自动检查）

```bash
git add .
git commit -m "feat: 实现XX功能"
```

**自动发生**：
1. 🎨 Black自动格式化代码
2. 🔧 Ruff自动修复lint问题
3. 🔍 Mypy类型检查

如果检查失败，修复问题后重新commit即可。

### 3. 推送代码（自动测试）

```bash
git push -u origin feat/4-issue-description
```

**自动发生**：
1. 🧪 运行所有测试
2. 📊 检查覆盖率（>50%）

如果测试失败，修复后重新push即可。

### 4. 创建PR

```bash
gh pr create \
  --title "feat: 实现XX功能" \
  --body "Closes #4"
```

**不要立即合并！** 等待CI通过。

### 5. 开始下一个Issue（无需等待PR合并）

```bash
# 切回main开始下一个issue
git checkout main
git checkout -b feat/5-next-issue

# 继续开发...
```

### 6. 合并PR（仅在CI通过后）

```bash
# 检查CI状态
gh run list --branch feat/4-issue-description --limit 1

# ✅ CI通过 → 合并
gh pr merge 15 --merge --delete-branch

# ❌ CI失败 → 切回分支修复
git checkout feat/4-issue-description
# 修复问题...
just check  # 本地验证
git push
```

## 故障排除

### Pre-commit hook失败

```bash
# 查看失败原因
git commit -v

# 自动修复
just fix

# 重新提交
git add .
git commit
```

### Pre-push hook失败（测试失败）

```bash
# 运行测试查看详情
poetry run pytest -v

# 修复测试后
git push
```

### CI失败但本地通过

**这不应该发生！** 如果发生了：

1. 确保本地配置是最新的：
   ```bash
   git pull
   poetry install --extras dev
   pre-commit install
   pre-commit install --hook-type pre-push
   ```

2. 运行完整检查：
   ```bash
   just check
   ```

3. 如果本地通过但CI失败，说明配置不一致 → 立即报告问题

## 工具版本

所有工具版本在`pyproject.toml`中统一管理：

- Black: 24.1.1
- Ruff: 0.8.4
- Mypy: 1.14.0
- Pytest: 8.3.4

**不要**在`.pre-commit-config.yaml`中重复指定配置（line-length等），避免不一致。

## 常用命令速查

| 命令 | 说明 | 耗时 |
|------|------|------|
| `just check` | 完整检查（推送前必须） | ~15秒 |
| `just check-quick` | 快速检查（提交前） | ~5秒 |
| `just fix` | 自动修复格式问题 | ~3秒 |
| `just test` | 运行测试 | ~5秒 |
| `just test-cov` | 测试+覆盖率报告 | ~10秒 |

## 记住

> **"本地能发现的问题，绝不让CI发现"**

推送前运行`just check`是你的责任，也是保持main分支绿色的关键。
