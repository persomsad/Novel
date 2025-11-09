# ADR-003: LangGraph Chapter Workflow

## 元信息
- 创建：2025-11-09
- 最近一次更新：2025-11-09
- 状态：draft
- 版本：v1
- 关联 Issue：#46, #45

---

## 背景

v0.2.0 引入 NervusDB 记忆、连续性索引与脚本校验，但 CLI 仍是“一问一答”的 ReAct 流程，无法保证“检索→写作→验证”按固定步骤执行。我们需要一个编排化的写作工作流来：

1. 自动收集资料（章节摘要、Nervus 事实、索引）
2. 根据资料写草稿
3. 统一调用脚本检查（时间线/引用）
4. 输出含问题清单的结果

这也为后续扩展（如多 Agent 协作、自动发布）打基础。

---

## 决策

### 1. 使用 LangGraph StateGraph 构建 `chapter_workflow`
- 状态类型：`ChapterState = {prompt, outline, draft, issues, context}`
- 节点：
  - `gather`：整合章节摘要 + Nervus 查询 + 用户需求
  - `draft`：调用 LLM 根据 `outline` 输出草稿
  - `verify`：运行 `verify_strict_timeline` / `verify_strict_references`，生成问题总结
- 边：`ENTRY -> gather -> draft -> verify -> END`
- 模型由 `ChatGoogleGenerativeAI` 或外部 Runnable 提供，保持注入式设计。

### 2. Reuse CLI/索引/Nervus
- workflow 构建时默认加载 `data/continuity/index.json`（若缺失则运行 `refresh-memory`）。
- 可选参数 `--nervus-db`，调用 `nervus_cli.cypher_query` 取部分事实，写入 `context`。
- 校验阶段直接复用现有脚本结果，确保 CLI 与 workflow 使用同一真相源。

### 3. CLI 入口
- `novel-agent run chapter --prompt ... [--prompt-file] [--nervus-db] [--no-refresh]`。
- 控制台输出 Outline/Draft/Issues，便于人工 review。

---

## 备选方案

### A. 继续使用单 ReAct Agent
- 优点：无需额外代码。
- 缺点：步骤不可控（顺序、重试、回滚都难做），无法统一调用脚本。

### B. MCP/外部编排
- 优点：可扩展。
- 缺点：集成成本高、超出 v0.2.0 范围。

---

## 后果

### 正面
- 工作流明确可观测：每个节点输出可日志化。
- 统一引用脚本 & Nervus 数据，减少重复解析。
- CLI 用户可以一条命令获取草稿+问题清单。

### 负面
- 需要维护额外模块（`workflows.py`）及依赖（LangGraph）。
- 目前仍是线性流程，尚未处理失败回滚；后续可增扩。

---

## 跟进
- [ ] workflow 完整日志与调试文档
- [ ] 后续考虑将 `continuity-editor/style-smith` 嵌入 workflow（多 Agent）
- [ ] 当需求稳定后，将本 ADR 状态更新为 active
