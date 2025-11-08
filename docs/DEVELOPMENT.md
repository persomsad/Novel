# 开发指南

## 🔴 推送前必读

**铁律**：推送前必须运行完整检查，确保本地和CI检查一致。

```bash
just check
```

如果通过，才能安全推送：

```bash
git push
```

## 本地检查命令

### 完整检查（推送前必须运行）

```bash
just check
```

这会运行**与CI完全相同**的检查：
1. Black - 格式检查
2. Ruff - Lint检查
3. Mypy - 类型检查
4. Pytest - 测试 + 覆盖率

### 快速检查（提交前）

```bash
just check-quick
```

只运行格式和lint检查（约5秒）。

### 自动修复

```bash
just fix
```

自动修复格式和lint问题。

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

### 2. 提交代码

```bash
# 快速检查
just check-quick

# 提交
git add .
git commit -m "feat: 实现XX功能"
```

**Pre-commit hook会自动运行**：
- Black格式化
- Ruff lint + 自动修复
- Mypy类型检查

### 3. 推送前完整检查

```bash
# 🔴 关键步骤：运行完整检查
just check

# 通过后才推送
git push -u origin feat/4-issue-description
```

**Pre-push hook会自动运行**：
- Pytest测试（所有测试必须通过）

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
