# ADR-002: NervusDB 记忆与知识基座集成

## 元信息
- 创建：2025-11-09
- 最近一次更新：2025-11-09
- 状态：draft
- 版本：v1
- 关联 Issue：#43, #45, #46 (后续补齐更多具体 issue)

---

## 背景

现有 Novel Agent 仅依赖：
1. LangGraph `SqliteSaver` 记录会话态（短期记忆）；
2. Markdown/JSON 文件存储章节、设定（长期文本），由 LLM 直接 `read_file`；
3. 计划中的连续性索引 `data/continuity/index.json`（结构化但仅本地文件）。

问题：
- 向量检索方案被判定“质量差”且不符合 Linus 哲学（复杂但不可解释）。
- 脚本/Agent 无法回答“谁在什么时间做了什么”这类需要关系+时间线的查询。
- 创作流程缺少统一、可复用的事实库，导致一致性验证必须重复解析文件。

机会：
- NervusDB (`@nervusdb/core`) 提供嵌入式三元组 + Temporal Memory，支持结构化事实与时间线、可验证关系、可扩展查询（QueryBuilder/Cypher/GraphQL/Gremlin）。
- 官方 CLI、插件、原生/JS 版本齐备，适合本地/边缘场景。

因此需要将 NervusDB 作为“长期记忆与知识基座”，替代向量方案，形成：
- **SqliteSaver**：会话状态（短期记忆）
- **NervusDB**：事实 + 时间线（长期记忆）
- **文件系统**：原始章节与设定（真相来源）

---

## 决策

### 1. NervusDB 作为长期记忆后端
- 采用官方 npm 包 `@nervusdb/core`（Node 18+，pnpm 管理），在仓库 `services/nervusdb` 目录提供以下能力：
  - `memory-gateway.ts`：HTTP/Unix Socket 服务，暴露 `POST /facts/ingest`、`POST /timeline/query`、`POST /graph/query` 等接口；
  - CLI 封装：`pnpm memory:ingest`、`pnpm memory:stats` 等，供 Python 调用；
  - 配置文件（例如 `memory.config.json`）描述数据库路径、插件、压缩选项。
- 数据模型：
  - `FactInput = { subject, predicate, object, properties }`
  - 时间线：借助 `TemporalMemoryStore` + `TemporalMemoryIngestor` 将章节叙事/对话转换为 episode/fact/timeline。
- 默认运行在本地同机，可作为嵌入式库或独立 Node 进程，支持热重启与 CLI 运维（`nervusdb stats/bench/gc/...`）。

### 2. Python 侧 Gateway 与工具
- 新增模块 `novel_agent/memory_gateway.py`（或 `tools_nervusdb.py`），封装与 Node 服务的 IPC/HTTP 交互，并暴露下列 LangChain Tool：
  1. `nervus_query(criteria)`：执行结构化事实查询（QueryBuilder/Cypher），返回 JSON。
  2. `nervus_timeline(entity, predicate?, range?)`：查询时间线，返回带时间戳的事件序列。
  3. `nervus_ingest(payload)`：把新章节/设定/对话写入 NervusDB（用于流程型 ingest）。
  4. （可选）`nervus_pathfind`, `nervus_aggregate` 等专用工具。
- Agent system prompt 更新：在“需要结构化信息或时间线时必须调用 NervusDB 工具”，明确输入格式（subject/predicate/properties/时间过滤）。

### 3. 数据管道
1. `refresh-memory`（Issue #43）负责扫描 `chapters/`、`spec/knowledge/`，生成：
   - `data/continuity/index.json`（供脚本/Agent 直接读取）；
   - `data/continuity/facts.ndjson`（NervusDB ingest 输入）。
2. `novel-agent memory ingest` 命令：
   - 调用 Node CLI/HTTP 将 facts/timeline 写入 NervusDB；
   - 可增量运行（基于章节 hash/version 字段）。
3. LangGraph Workflow（Issue #46）按步骤调用：
   - `nervus_query` 获取角色/事件关系；
   - `nervus_timeline` 获得时间顺序；
   - LLM 撰写草稿 → `verify_*` 脚本对比 NervusDB 事实 → 输出。

### 4. 一致性脚本联动
- 时间线/引用脚本除解析 Markdown，还需对比 NervusDB 查询结果：
  - 若章节写出与 NervusDB 事实不一致，脚本报告“章节 vs 事实库”差异；
  - 脚本也可用 NervusDB 计算“是否存在引用实体/事件”。
- 长期目标：脚本只解析章节 → 生成事实 → 与 NervusDB 对比，保持单一真相源。

### 5. 运维 & CI
- Node 服务提供 `npm run memory:check`：运行 `nervusdb check/repair/stats` 等命令确保数据库健康。
- CI 中的 `just ci` 增加步骤：
  1. 启动临时 NervusDB；
  2. 运行 `refresh-memory` + `memory ingest`；
  3. 执行 e2e 流程（workflow + check），验证 Gateway/工具可用。
- README 与 `docs/memory.md`（新增）讲清部署、配置、API 调用、常见问题。

---

## 方案分析

### 为什么不用向量数据库？
- 缺少结构化关系 → 无法直接回答“谁与谁在何时发生了哪种关系”；
- 相似度召回难以审计，容易产生幻觉；
- NervusDB 提供 deterministic 查询 + 时序 API + 插件（pathfinding/aggregation），满足 Agent 和一致性检查对“真相”和“追溯”的需求。

### NervusDB 集成的风险
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Node 18+/pnpm 环境不一致 | CLI/CI 无法运行 | 在 repo 中提供 `.node-version` + pnpm 安装脚本；CI 使用 actions/setup-node |
| 同步延迟（文件已改但未 ingest） | Agent 查询到旧事实 | `refresh-memory` + `memory ingest` 合并成单命令，作为写作 workflow 的第一步；CLI 提醒 |
| NervusDB 体积增长 | 本地磁盘压力 | 提供 `nervusdb compact/gc` 脚本；定期自动运行 |
| 多进程并发访问 | 锁冲突 | 默认启用 `enableLock`，写操作通过 gateway 排队；LangGraph 侧仅在必要时写入 |
| LLM 生成错误查询 | 报错或空结果 | Prompt 中提供 Query 模板 + 参数检查，gateway 校验参数（白名单 predicate/label） |

---

## 实施计划（映射到 Issue）

1. **#43 连续性索引**
   - 产出 `index.json` + `facts.ndjson` + `timeline.ndjson`。
2. **新增 Issue：NervusDB Gateway 服务**
   - Node 项目、HTTP API、Docker/PM2 启动脚本、基本测试。
3. **#45 会话持久化与 NervusDB 记忆接入**
   - Python Gateway + LangChain Tools + CLI `memory ingest` + README。
4. **#46 LangGraph Workflow**
   - 在节点中调用 `nervus_query/timeline`。
5. **新增 Issue：一致性脚本对比 NervusDB**
   - Timeline/Reference 校验包含 NervusDB 事实差异。
6. **文档**
   - README 增加 NervusDB 部署章节；`docs/memory.md` 记录操作指南；ADR 更新状态为 active。

---

## 后果

### 正面
1. **结构化长期记忆**：事实 + 时间线均可查询与追踪。
2. **可审计/可解释**：查询语句与结果明确，支持日志记录。
3. **流程闭环**：`章节 → 索引 → NervusDB → Workflow/脚本`，消除多处解析。
4. **扩展能力**：可用 Cypher/GraphQL/Gremlin/插件实现更复杂的推理（路径、聚合、空间等）。

### 负面
1. **技术栈新增 Node/pnpm**：Python 项目需维护额外运行环境。→ 通过脚本/文档最小化心智负担。
2. **部署复杂度上升**：需要启动 NervusDB 服务。→ 提供 `just memory-demo`、Docker compose。
3. **同步成本**：章节更新 → 需 rerun ingest。→ 写作 workflow 自动执行。

---

## 跟进

- [ ] 完成 NervusDB Gateway 与 CLI 工具。
- [ ] 在 README/Docs 中提供完整操作指南。
- [ ] Issue #45/#46/#?? 合并时更新本 ADR 状态为 `active`。
- [ ] 监控磁盘/性能，必要时引入原生核心或集群部署（未来 ADR）。

---

## 变更记录
- 2025-11-09：v1 草稿，定义 NervusDB 集成方向与执行计划。
