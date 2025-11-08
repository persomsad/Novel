# ADR-001: 小说写作 CLI Agent 技术方案

## 元信息
- 创建：2025-01-08
- 最近一次更新：2025-01-08
- 状态：active
- 版本：v1

---

## 背景

### 项目目标
构建一个基于 LLM 的 CLI 小说写作助手，支持对话式创作和智能一致性检查。

### 核心功能
1. **对话式创作**：通过自然语言与 Agent 交互，创建和修改章节
2. **智能一致性检查**：利用 ReAct Agent 的推理能力，检查角色、情节、时间线一致性
3. **会话持久化**：保存创作历史，支持多轮对话
4. **文件管理**：自动组织章节、设定、大纲等文件

### 核心洞察（来自 ReAct 架构研究）
**ReAct (Reasoning + Acting) 的关键发现**：
- LLM 的推理能力可以用来分析复杂问题，无需为每种检查创建专门工具
- Agent 可以通过 `read_file` + 推理完成**语义层面**的一致性检查
- 脚本仅用于**精确验证**（时间、数字、引用 ID）

**示例**：
```
用户："检查第3章角色是否一致"

Agent 推理过程：
Thought: 我需要先了解角色设定，然后读取第3章对比
Action: read_file("spec/knowledge/character-profiles.md")
Observation: 主角性格：善良但缺乏自信

Action: read_file("chapters/chapter-003.md")
Observation: 第3章主角突然变得非常勇敢...

Thought: 发现矛盾！主角设定"缺乏自信"，但第3章"非常勇敢"
Final Answer: ⚠️ 角色一致性问题 + 修复建议
```

### 团队约束
- 单人开发
- 1周内完成 MVP
- 优先实用性，避免过度设计

---

## 决策

### 1. 技术栈选型

#### 核心技术
- **语言**：Python 3.12
  - **理由**：LangChain 官方支持最佳，生态成熟，开发效率高
  
- **Agent 框架**：LangChain 1.0.4 + LangGraph
  - **理由**：
    - LangChain 1.0 简化了 API（`create_agent` 替代 `create_react_agent`）
    - LangGraph 提供状态管理和工作流控制
    - 官方文档完善，社区活跃

- **LLM**：Google Gemini 2.0 Flash Exp
  - **理由**：
    - 免费且性能优秀（比 Gemini 1.5 Pro 更快）
    - 中文支持好（适合小说创作）
    - 上下文窗口大（适合处理长文本）
    - ⚠️ 风险：质量可能不如 GPT-4，需要强化 system prompt

#### 辅助工具
- **CLI 框架**：Typer + Rich
  - **理由**：Typer 简单易用，Rich 提供美观的终端输出
  
- **状态管理**：LangGraph MemorySaver
  - **理由**：内置持久化方案，支持会话恢复

---

### 2. 架构模式

#### 架构类型
- **单体 ReAct Agent**（非 Plan-and-Execute，非多 Agent）
  - **理由**：
    - MVP 阶段，功能简单，单 Agent 足够
    - ReAct 循环（Thought → Action → Observation）透明度高
    - 避免 Plan-and-Execute 的过度规划问题

#### 工具设计（关键决策）
**核心理念**：**ReAct Agent 的推理能力 > 外部工具**

##### 基础工具（3个，必需）
1. `read_file(path)` - 读取任意文件
2. `write_chapter(number, content)` - 创建新章节
3. `search_content(keyword)` - 搜索关键词

##### 验证工具（2个，可选）
4. `verify_strict_timeline()` - 时间线精确验证（调用脚本）
5. `verify_strict_references()` - 引用完整性验证（调用脚本）

**为什么只有 5 个工具？**
- ✅ **简洁 > 复杂**：Agent 的推理能力已经足够强大
- ✅ **不需要专门的检查工具**：Agent 通过 `read_file` + 推理即可完成一致性检查
- ✅ **脚本仅用于兜底**：处理精确的数字/时间/引用检查

**工作流示例**：
```
1. 用户："检查第3章角色是否一致"
2. Agent推理：我需要读取角色设定和第3章
3. Agent调用：read_file("spec/knowledge/character-profiles.md")
4. Agent调用：read_file("chapters/chapter-003.md")
5. Agent推理：对比分析，发现矛盾
6. Agent输出：详细的问题报告和修复建议
```

#### 数据存储
- **方案**：文件系统（Markdown 文件）
  - **理由**：
    - 符合现有工作流（用户已经在用 Markdown）
    - 易于版本控制（Git）
    - 无需数据库，降低复杂度

- **目录结构**：
  ```
  Novel/
  ├── chapters/          # 章节
  │   ├── ch001.md
  │   └── ch002.md
  ├── spec/
  │   ├── knowledge/     # 设定
  │   │   ├── character-profiles.md
  │   │   ├── world-setting.md
  │   │   └── magic-system.md
  │   └── outline.md     # 大纲
  └── .novel-agent/
      └── sessions/      # 会话持久化
          └── session_123.json
  ```

#### 会话管理
- **方案**：LangGraph MemorySaver（文件持久化）
  - **理由**：
    - 内置方案，无需自己实现
    - 支持自动保存/恢复
    - 存储在 `.novel-agent/sessions/`

---

### 3. 质量保障

#### 代码质量
- **格式化**：Black（line-length=100）
- **Lint**：Ruff + mypy（strict mode）
- **配置**：
  ```toml
  # pyproject.toml
  [tool.black]
  line-length = 100
  
  [tool.ruff]
  line-length = 100
  select = ["E", "F", "I", "N", "W"]
  
  [tool.mypy]
  strict = true
  ```

#### 测试策略
- **框架**：pytest
- **覆盖率**：>70%
- **测试类型**：
  - 单元测试：工具函数（read_file, write_chapter）
  - 集成测试：完整 Agent 工作流
  - Mock LLM：使用 `langchain.llms.fake.FakeListLLM`

#### 自动化门槛
- **本地**：pre-commit hooks
  - commit 时：black --check, ruff check, mypy
  - push 时：pytest（完整测试）
  
- **CI**：GitHub Actions
  - Lint + Test + Build
  - Python 版本：3.12（固定版本，避免兼容性问题）

---

### 4. 发布流程

#### 构建工具
- **Poetry**（官方推荐）
  - **理由**：
    - 依赖管理 + 虚拟环境 + 打包一体化
    - 生成 `poetry.lock` 保证可重复构建
    - 发布到 PyPI 方便

#### 版本管理
- **策略**：SemVer（语义化版本）
  - v0.1.0: MVP（基础 Agent + 5 个工具）
  - v0.2.0: 添加新功能（如导出功能）
  - v1.0.0: 稳定版（所有核心功能完成）

#### 发布节奏
- **v0.1.0**：1 周内完成（MVP）
- **后续版本**：按需迭代（基于真实使用反馈）

#### 部署方式
- **目标环境**：本地开发环境
- **安装方式**：
  ```bash
  pip install novel-agent
  novel-agent chat  # 启动对话
  ```

---

## 备选方案

### 备选方案 A：Plan-and-Execute 架构

**优点**：
- 先规划再执行，适合复杂多步骤任务
- 执行过程更结构化

**缺点**：
- 过度规划问题（"分析瘫痪"）
- 增加复杂度，不适合 MVP
- 调试困难

**放弃原因**：ReAct 循环更简单、透明，适合快速迭代

---

### 备选方案 B：GPT-4 + OpenAI API

**优点**：
- 质量更高（GPT-4 比 Gemini 强）
- API 稳定性好

**缺点**：
- 收费（GPT-4 成本高）
- 中文支持不如 Gemini

**放弃原因**：MVP 阶段优先免费方案，后续可支持多 LLM

---

### 备选方案 C：7 个工具（包含专门的检查工具）

**原始设计**：
- check_character_consistency()
- check_plot_consistency()
- check_timeline_consistency()

**优点**：
- 检查类型明确
- 调用简单

**缺点**：
- ❌ **过度设计**：Agent 自己就能通过推理完成检查
- ❌ **灵活性差**：无法处理新类型的检查
- ❌ **维护成本高**：每种检查都要写脚本

**放弃原因**：ReAct Agent 的推理能力足以处理语义检查，只保留精确验证脚本

---

### 备选方案 D：多 Agent 架构

**设计**：
- 创作 Agent（写章节）
- 检查 Agent（检查一致性）
- 协调 Agent（分配任务）

**优点**：
- 职责分离
- 可扩展性好

**缺点**：
- 复杂度高
- 调试困难
- MVP 阶段不必要

**放弃原因**：单 Agent 足够，后续可升级

---

### 备选方案 E：MCP 集成

**优点**：
- 可以调用外部服务（如搜索引擎）
- 扩展性强

**缺点**：
- 增加复杂度
- MVP 阶段不需要

**放弃原因**：延后到 v0.2.0+

---

## 后果

### 正面收益
1. **快速验证**：1 周完成 MVP，快速验证 ReAct 方案可行性
2. **简洁架构**：5 个工具 + 单 Agent，易于理解和维护
3. **智能检查**：利用 LLM 推理，无需为每种检查写规则
4. **低成本**：Gemini 免费，降低试验成本
5. **灵活扩展**：架构简单，后续可轻松添加新功能

### 负面代价

#### 1. Gemini 质量风险
- **问题**：Gemini 质量可能不如 GPT-4，导致检查不准确
- **缓解措施**：
  - 强化 system prompt（参考 `NOVEL_AGENT.md` 的 XML 结构）
  - 集成 `personal-voice.md`（个人写作风格）
  - 添加示例（few-shot learning）
  - v0.2.0 支持切换 LLM（OpenAI/Claude）

#### 2. 文件系统性能
- **问题**：大量章节时，文件 I/O 可能慢
- **缓解措施**：
  - v0.1.0 限制章节数量（<100）
  - 添加缓存机制（后续版本）
  - 若性能瓶颈，可迁移到 SQLite

#### 3. 会话持久化风险
- **问题**：MemorySaver 数据丢失
- **缓解措施**：
  - 每次对话结束自动保存
  - 定期备份 `.novel-agent/sessions/`
  - 添加恢复机制

#### 4. 精确检查覆盖不全
- **问题**：仅 2 个验证脚本，可能漏掉某些精确检查
- **缓解措施**：
  - v0.1.0 专注核心场景（时间线、引用）
  - 用户反馈后按需添加新脚本
  - Agent 推理能发现大部分问题

---

## 跟进与验证

### v0.1.0 验证清单

#### P0 - 必须验证（阻塞发布）
- [ ] **项目初始化**
  - [ ] 使用 `poetry new novel-agent` 创建项目
  - [ ] 配置 `pyproject.toml`（依赖、脚本）
  - [ ] 创建目录结构（src/novel_agent/）
  
- [ ] **核心 Agent**
  - [ ] 实现 5 个工具（read_file, write_chapter, search_content, verify_strict_timeline, verify_strict_references）
  - [ ] 配置 Gemini API 连接
  - [ ] 实现 ReAct Agent（使用 LangChain `create_agent`）
  - [ ] 验证：Agent 能完成"创建第1章"任务

- [ ] **一致性检查验证**
  - [ ] 测试：Agent 能发现角色性格矛盾
  - [ ] 测试：Agent 能发现情节逻辑问题
  - [ ] 测试：脚本能检查时间线数字错误
  - [ ] 测试：脚本能检查引用 ID 不存在

- [ ] **CLI 界面**
  - [ ] 使用 Typer 实现命令（`novel-agent chat`）
  - [ ] 使用 Rich 美化输出（彩色、进度条）
  - [ ] 验证：用户能通过对话创建章节

#### P1 - 重要但非阻塞
- [ ] **配置自动化**
  - [ ] 创建 `.pre-commit-config.yaml`
  - [ ] 创建 `.github/workflows/ci.yml`
  - [ ] 验证：pre-commit hooks 工作正常

- [ ] **测试覆盖**
  - [ ] 单元测试：每个工具函数
  - [ ] 集成测试：完整创作流程
  - [ ] 覆盖率：>70%

- [ ] **文档**
  - [ ] `README.md`（安装、使用、示例）
  - [ ] `docs/tools-specification.md`（工具详细说明）
  - [ ] `docs/architecture/index.md`（ADR 索引）

#### P2 - 后续版本
- [ ] 性能优化（缓存、批量处理）
- [ ] 支持多 LLM（OpenAI/Claude）
- [ ] MCP 集成（外部服务）
- [ ] 导出功能（PDF/EPUB）

---

## 变更记录
- v1 - 2025-01-08：初始决策
  - 确定技术栈（Python 3.12 + LangChain + Gemini）
  - 确定架构（单 ReAct Agent + 5 工具）
  - 放弃 7 工具方案，采用"Agent 推理优先，脚本兜底"策略
