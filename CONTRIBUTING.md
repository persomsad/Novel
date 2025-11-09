# Contributing Guide

感谢对 Novel Agent 的贡献！在提交 Issue/PR 前，请遵循以下流程，确保与 v0.2.0 技术决策保持一致。

## 环境准备

1. Python 3.12，推荐使用 Poetry：
   ```bash
   poetry install
   poetry shell
   ```
2. 安装 pre-commit：
   ```bash
   just setup-hooks
   ```
3. 若需要 Nervus CLI，参考 `docs/memory-cli.md` 安装 `@nervusdb/core` 并设置 `NERVUSDB_BIN`。

## 提交流程

1. **创建分支**：以 Issue 为单位，例如 `feat/50-docs-sync`。
2. **实现功能**并同步文档（README、ADR、docs/tools-specification）。
3. **本地验证**（与 CI 相同）：
   ```bash
   just check          # black + ruff + mypy + pytest + coverage
   poetry run novel-agent refresh-memory
   # 如涉及 Nervus 记忆：
   # poetry run novel-agent memory ingest --db demo.nervusdb --dry-run
   ```
4. **运行新增工作流/命令示例**，将关键日志附在 PR 描述中。
5. **提交前检查**：
   - `git status` 保持干净
   - `README` + `docs/architecture` + `docs/tools-specification` 已更新
   - 对应 Issue 在 PR 描述中使用 `Closes #<id>` 关联

## PR 要求

- 至少更新一个 ADR / 文档段落，说明变更理由。
- README 中的命令示例需能够复制运行。
- 若新增 CLI/脚本，必须附测试或最少示例输出。
- 简单脚本/命令输出即可作为“冒烟测试”粘贴在 PR 描述末尾。

更多背景参考：
- `docs/architecture/ADR-001-cli-agent-architecture.md`
- `docs/architecture/ADR-002-nervusdb-memory.md`
- `docs/architecture/ADR-003-chapter-workflow.md`

欢迎在 Issue 内留言或直接提交草稿 PR，我们会根据里程碑安排 Review。
