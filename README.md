# Novel Agent

基于 LangChain + LangGraph 的智能小说写作助手，支持对话式创作和自动一致性检查。

## 特性

- ✅ **对话式创作**：通过自然语言与 Agent 交互，创建和修改章节
- ✅ **智能一致性检查**：利用 ReAct Agent 的推理能力，自动检查角色、情节、时间线一致性
- ✅ **会话持久化**：保存创作历史，支持多轮对话
- ✅ **文件管理**：自动组织章节、设定、大纲等文件

## 核心技术

- **LLM**：Google Gemini 2.0 Flash Exp
- **框架**：LangChain 1.0.4 + LangGraph
- **架构**：ReAct (Reasoning + Acting) Agent
- **工具**：5 个核心工具（读取、写入、搜索、验证）

## 安装

### 前置要求

- Python 3.12+
- Poetry（推荐）或 pip

### 使用 Poetry（推荐）

```bash
# 克隆项目
git clone https://github.com/your-username/novel-agent.git
cd novel-agent

# 安装依赖
poetry install

# 激活虚拟环境
poetry shell

# 运行
novel-agent chat
```

### 使用 pip

```bash
pip install novel-agent
novel-agent chat
```

## 快速开始

### 1. 配置 API Key

```bash
export GOOGLE_API_KEY="your-gemini-api-key"
```

### 2. 启动对话

```bash
novel-agent chat
```

### 3. 示例对话

```
> 你好，我想写一部科幻小说

Agent: 您好！我是小说写作助手。科幻小说的创作需要先明确几个要素...
请问您有初步的故事设定吗？

> 帮我创建第1章，主角在2077年的赛博朋克城市中醒来

Agent: 好的，我将为您创建第1章。请稍等...
[调用 write_chapter(1, content)]
✅ 第1章已创建：chapters/ch001.md

> 检查第1章的角色描写是否符合设定

Agent: 我来检查第1章的角色一致性...
[调用 read_file("spec/knowledge/character-profiles.md")]
[调用 read_file("chapters/ch001.md")]
[推理分析...]
✅ 检查完成！发现 1 个问题：主角性格描写与设定有差异...
```

## 项目结构

```
Novel/
├── chapters/              # 章节（Agent 自动创建）
│   ├── ch001.md
│   └── ch002.md
├── spec/
│   ├── knowledge/         # 设定
│   │   ├── character-profiles.md
│   │   ├── world-setting.md
│   │   └── magic-system.md
│   └── outline.md         # 大纲
├── .novel-agent/
│   └── sessions/          # 会话持久化
│       └── session_123.json
├── src/novel_agent/       # Agent 源码
│   ├── cli.py
│   ├── agent.py
│   └── tools.py
└── docs/
    └── architecture/      # 技术文档
        └── ADR-001-cli-agent-architecture.md
```

## 核心工具

Agent 可以调用 5 个工具：

### 基础工具（3 个）
1. **`read_file(path)`** - 读取任意文件
2. **`write_chapter(number, content)`** - 创建新章节
3. **`search_content(keyword)`** - 搜索关键词

### 验证工具（2 个）
4. **`verify_strict_timeline()`** - 时间线精确验证
5. **`verify_strict_references()`** - 引用完整性验证

## 一致性检查原理

**关键洞察**：ReAct Agent 通过**推理能力**完成大部分一致性检查，无需专门的检查工具。

### 示例：检查角色一致性

```
用户："检查第3章角色是否一致"

Agent 推理过程：
1. Thought: 我需要先了解角色设定
   Action: read_file("spec/knowledge/character-profiles.md")
   Observation: 主角性格：善良但缺乏自信

2. Thought: 现在读取第3章内容
   Action: read_file("chapters/chapter-003.md")
   Observation: 第3章主角突然变得非常勇敢...

3. Thought: 发现矛盾！设定说"缺乏自信"，但第3章"非常勇敢"
   Final Answer: ⚠️ 角色一致性问题 + 详细修复建议
```

### Agent 能检查什么？

✅ **语义层面**（Agent 推理）：
- 角色性格前后矛盾
- 情节逻辑不合理
- 时间线不符合常识
- 世界观规则被打破

✅ **精确层面**（脚本验证）：
- 时间数字错误（"第2天晚上 → 第2天早上"）
- 引用 ID 不存在（"第10章引用第5章伏笔，但第5章不存在"）

## NervusDB 长期记忆（v0.2.0 规划中）

> 为什么不用向量数据库？因为我们需要“谁在何时做了什么”这类可追溯的事实，而不是模糊相似度。

自 v0.2.0 起，项目会把 NervusDB 作为长期记忆与知识基座（详见 `docs/memory-cli.md`），整体流程如下：

1. **准备环境**
   - Node.js ≥ 20，已安装 `pnpm`
   - `pnpm install`（根目录）后，运行 `pnpm install --filter services/nervusdb`（服务子目录将在实现时提供）
2. **构建连续性索引**
   - `just refresh-memory`（#43）会生成 `data/continuity/index.json` + `facts.ndjson`
3. **写入 NervusDB**
   - `novel-agent memory ingest`（#45）会调用 Node Gateway，将章节/设定事实与时间线写入 NervusDB
4. **运行 Gateway**
   - `pnpm --filter services/nervusdb memory:dev` 启动 HTTP/Unix Socket 服务
   - CLI 仍可使用 `nervusdb stats|check|bench` 等命令维护数据库
5. **Agent 调用**
   - 新增 LangChain Tools：`nervus_query`（结构化事实查询）、`nervus_timeline`（时间线）、`nervus_ingest`（增量写入）
   - LangGraph Workflow（#46）在规划/草稿阶段自动查询 NervusDB，再结合脚本验证
   - 设置 `NERVUSDB_DB_PATH` 后，`verify_strict_timeline` / `verify_strict_references` 会自动与 NervusDB 对比，报告“章节 vs 数据库”的差异

> 详细的架构与操作指南见 `docs/architecture/ADR-002-nervusdb-memory.md`。在 v0.2.0 合并前，以上命令/路径可能有轻微调整。

## Agent 类型

| 类型 | 用途 | 工具组合 |
|------|------|-----------|
| `default` | 通用创作 + 一致性检查 | read_file, write_chapter, search_content, verify_* |
| `outline-architect` | 大纲设计、情节规划 | read_file, search_content |
| `continuity-editor` | 连续性稽核，按“思考→规划→草稿→修订”产出问题/修复建议 | read_file, search_content, verify_* |
| `style-smith` | 文风润色、再创作，输出新段落 + 改动说明 | read_file, search_content, write_chapter |

通过 `novel-agent chat --agent <type>` 切换角色。未来还会在 workflow 中将它们编排组合。

### 创作辅助工具（程序内可直接调用）

- `calculate_word_count(text)`：统计字符、词数、句子数与平均句长。
- `random_name_generator(genre, gender, seed=None)`：根据类型/性别输出稳定的人名。
- `style_analyzer(text)`：返回语气推断、感叹/省略比、形容词命中等指标。
- `dialogue_enhancer(dialogue_text, character_hint=None)`：为对白自动添加动作描写。
- `plot_twist_generator(current_plot, intensity='medium')`：生成 3 条反转思路。

这些函数位于 `src/novel_agent/tools_creative.py`，可在 prompt eval、workflow 或 CLI 扩展中复用。

## 会话管理

- 默认会话保存在 `.novel-agent/state.sqlite`。
- 使用 `novel-agent chat --session hero-arc` 可以延续特定会话，便于多轮创作。
- `novel-agent sessions --list` 查看所有线程；`novel-agent sessions --delete <id>` 清理旧会话。
- 会话底层由 LangGraph `SqliteSaver` 支持，可在多次 CLI 运行之间恢复状态。

## 连续创作流程

1. **刷新索引**：`poetry run novel-agent refresh-memory` → 生成 `data/continuity/index.json`。
2. **（可选）写入 NervusDB**：`poetry run novel-agent memory ingest --db path/to/demo.nervusdb`。
3. **运行 workflow**：`poetry run novel-agent run chapter --prompt "写李明的成长" --api-key $GOOGLE_API_KEY [--nervus-db ...]`。
4. **人工 Review**：终端输出 Outline、Draft、Issues，可再结合 `continuity-editor` / `style-smith` 进一步处理。

以上步骤确保“索引 → Nervus → Workflow → 脚本检查”形成闭环，避免遗忘设定或破坏时间线。

## 开发

### 安装开发依赖

```bash
poetry install
just setup-hooks  # 安装 pre-commit hooks
```

### 运行检查

```bash
# 完整检查（与 CI 一致）
just check

# 快速检查（commit 前）
just check-quick

# 自动修复格式问题
just fix

# 运行测试
just test

# 重新生成连续性索引
poetry run novel-agent refresh-memory

# 查看/删除持久化会话
poetry run novel-agent sessions --list
poetry run novel-agent sessions --delete hero-arc

# 将连续性索引写入 NervusDB
poetry run novel-agent memory ingest --db path/to/demo.nervusdb

# 运行章节 workflow
poetry run novel-agent run chapter --prompt "写一段李明的成长" --api-key $GOOGLE_API_KEY

# 启动 Nervus Gateway (Node)
pnpm install --filter services/nervusdb
pnpm --filter services/nervusdb memory:dev
```

### 提交代码

```bash
git add .
git commit -m "feat: add new feature"  # 会自动运行 pre-commit hooks
git push  # 会自动运行完整测试
```

## 技术文档

- [ADR-001: CLI Agent 技术方案](./docs/architecture/ADR-001-cli-agent-architecture.md)
- [架构决策记录索引](./docs/architecture/index.md)

## 路线图

### v0.1.0 (MVP) - 已完成 ✅
- [x] 项目初始化（Poetry + 配置文件）
- [x] 实现 5 个核心工具
- [x] 实现 ReAct Agent
- [x] CLI 界面（Typer + Rich）
- [x] 会话持久化
- [x] 一致性检查验证
- [x] 端到端测试
- [x] 错误处理和日志记录
- [x] 测试覆盖率 70%

### v0.2.0
- [ ] 支持多 LLM（OpenAI/Claude）
- [ ] 导出功能（PDF/EPUB）
- [ ] 性能优化

### v1.0.0
- [ ] 稳定版发布
- [ ] MCP 集成
- [ ] 高级功能

## 贡献

欢迎提交 Issue 和 PR！

## License

MIT
