# ADR-002: Orion架构集成方案

## 元信息
- 创建：2025-11-09
- 最后更新：2025-11-09
- 状态：Active
- 版本：v1
- 相关Issue：#12, #13, #14

## 背景

### 当前状态（v0.1.0）
- **技术栈**：Python 3.12 + LangChain + LangGraph
- **架构**：简单的ReAct Agent，5个基础工具
- **功能**：对话式创作、基础一致性检查、会话持久化
- **限制**：
  - 无完整编排流程（缺少plan/critic/rewrite节点）
  - 无知识图谱（角色/事件关系靠Agent推理）
  - 无引用追踪（无法自动标注来源）
  - 无可观测性（无指标/追踪/成本统计）
  - 无Prompt治理（提示词硬编码）

### Orion项目优势
经过分析Orion项目（TypeScript实现），发现以下生产级能力：

1. **完整的LangGraph编排**
   - 7节点流程：`ingest → plan → research → draft → critic → rewrite → approve`
   - 状态持久化和checkpoint
   - 支持人工干预和回退

2. **NervusDB知识图谱**
   - 三元组存储：`(subject, predicate, object)`
   - 查询模板：`get_character_view`, `get_events_between`, `find_sources`
   - 可重建缓存层

3. **Gemini深度集成**
   - Google Search Grounding（自动引用）
   - Structured Output（强类型输出）
   - 多模型支持（2.5 Pro/Flash）

4. **生产级质量保证**
   - 完整CI/CD流水线
   - ReAct metrics追踪
   - 成本统计（token usage/cost）
   - Nightly质量报告

5. **Prompt工程治理**
   - 版本化管理（`prompts/`目录）
   - 变更记录和评测
   - Rollback机制

### 集成需求
- v0.1.0已验证ReAct Agent可行性
- 现需升级到生产级：完整编排、知识图谱、可观测性
- 保持用户体验一致（CLI命令不变）
- 支持渐进式迁移（Python工具可复用）

## 决策

### 1. 技术栈：混合架构（Python + TypeScript）

**核心编排层：TypeScript**
- 使用Orion的LangGraph编排系统
- packages/orchestrator：状态机和节点定义
- packages/adapters：外部服务适配（Gemini/NervusDB）
- packages/cli：命令行入口

**工具层：保留Python**
- 复用v0.1.0的5个工具（read_file/write_chapter等）
- Python作为TypeScript调用的子进程
- 未来可选择性迁移到TypeScript

**理由**：
- Orion已验证TypeScript + LangGraph生产可行性
- Python工具无需重写，降低风险
- pnpm + workspace便于管理多包

### 2. 目录结构：Monorepo

```
Novel/
├── packages/                    # TypeScript包（新增）
│   ├── orchestrator/           # LangGraph编排核心
│   ├── cli/                    # TypeScript CLI
│   ├── adapters/
│   │   ├── gemini/            # Gemini API适配
│   │   ├── nervusdb/          # 知识图谱
│   │   └── python-tools/      # Python工具桥接
│   └── shared/                # 共享类型和工具
├── src/novel_agent/            # Python工具（保留）
│   ├── tools.py               # 5个基础工具
│   └── logging_config.py
├── docs/
│   ├── architecture/          # ADR文档
│   └── prompts/               # Prompt版本管理（新增）
├── scripts/                   # 质量检查脚本（新增）
├── e2e/                       # 端到端测试（新增）
├── pnpm-workspace.yaml        # pnpm配置（新增）
├── tsconfig.base.json         # TS配置（新增）
└── pyproject.toml             # Python配置（保留）
```

### 3. 编排流程：7节点LangGraph

```
┌─────────┐
│ ingest  │  接收用户请求（题目/受众/风格）
└────┬────┘
     ▼
┌─────────┐
│  plan   │  生成大纲（Gemini Structured Output）
└────┬────┘
     ▼
┌──────────┐
│ research │  查询NervusDB + Search Grounding
└────┬─────┘
     ▼
┌─────────┐
│  draft  │  逐段生成内容（含引用占位符）
└────┬────┘
     ▼
┌─────────┐
│ critic  │  质量评审（JSON格式问题清单）
└────┬────┘
     ├─问题 → ┌──────────┐
     │        │ rewrite  │  根据问题修订
     │        └────┬─────┘
     │             ▼
     └─通过 → ┌─────────┐
              │approve  │  人工审核/自动发布
              └─────────┘
```

**节点职责**：
- **ingest**: 验证输入、初始化状态
- **plan**: 生成结构化大纲（标题/段落/关键点）
- **research**: 查询知识库+外部资料，返回引用
- **draft**: 逐段写作，插入引用标记
- **critic**: 评估质量（事实性/逻辑/可读性/风格）
- **rewrite**: 根据问题清单修订（最多3次）
- **approve**: 人工审核或自动发布

### 4. 数据存储：三层架构

```
┌──────────────────────────────────┐
│  Markdown/JSON（单一真相来源）    │
│  - docs/people.md              │
│  - docs/timeline.md            │
│  - spec/tracking/*.json        │
└────────────┬─────────────────────┘
             │ 同步
             ▼
┌──────────────────────────────────┐
│  NervusDB（可重建缓存）           │
│  - 三元组：(角色, 关系, 值)       │
│  - 查询模板：快速检索             │
└────────────┬─────────────────────┘
             │ 查询
             ▼
┌──────────────────────────────────┐
│  LangGraph State（运行时）        │
│  - Checkpoint持久化              │
│  - 支持回滚和重放                 │
└──────────────────────────────────┘
```

**原则**：
- Markdown/JSON作为Git版本控制的真相
- NervusDB可随时从Markdown重建
- LangGraph State只在任务执行期间存在

### 5. Python ↔ TypeScript 桥接

**方案A：子进程调用（v0.2.0采用）**
```typescript
// packages/adapters/python-tools/src/index.ts
export async function callPythonTool(
  tool: 'read_file' | 'write_chapter' | ...,
  args: Record<string, any>
): Promise<any> {
  const result = await execFile('poetry', [
    'run', 'python', '-m', `novel_agent.tools.${tool}`,
    JSON.stringify(args)
  ]);
  return JSON.parse(result.stdout);
}
```

**方案B：HTTP API（未来可选）**
- Python启动FastAPI服务
- TypeScript通过HTTP调用
- 适合多实例部署

### 6. Gemini集成：官方SDK + Grounding

```typescript
// packages/adapters/gemini/src/index.ts
import { GoogleGenerativeAI } from '@google/genai';

export async function generateOutline(
  topic: string,
  audience: string
): Promise<OutlineSection[]> {
  const model = genAI.getGenerativeModel({
    model: 'gemini-2.5-flash',
    tools: ['googleSearch'], // Search Grounding
  });

  const result = await model.generateContent({
    systemInstruction: PLANNER_PROMPT,
    contents: [{ role: 'user', parts: [{ text: topic }] }],
    generationConfig: {
      response_schema: OutlineSchema, // Structured Output
    },
  });

  return result.response.candidates[0].content.parts[0].data;
}
```

### 7. 可观测性：全流程追踪

**指标收集**：
- 每个节点执行：时间/token/成本
- 失败统计：节点/原因/重试次数
- 质量指标：Critic评分/迭代次数

**输出格式**：
- `.agent/tasks/{taskId}/react-trace.jsonl`：追踪日志
- `.agent/reports/react-metrics.json`：汇总报告
- CI artifact：Nightly质量趋势

### 8. 迁移路线图

**Phase 1：基础架构（Issue #12-14）**
- ADR文档（本文档）
- TypeScript项目初始化
- LangGraph编排核心

**Phase 2：适配器实现（Issue #15-16）**
- Gemini适配器 + Search Grounding
- NervusDB集成
- Python工具桥接

**Phase 3：CLI和测试（Issue #17, 20）**
- CLI迁移到TypeScript
- 端到端测试

**Phase 4：可观测性（Issue #18-19）**
- ReAct Metrics
- Prompt治理

## 备选方案

### 备选方案A：纯Python实现
- **优点**：无需学习TypeScript，复用现有代码
- **缺点**：
  - Orion已验证TypeScript生态成熟
  - Python的LangGraph社区不如TypeScript活跃
  - NervusDB TypeScript SDK更完善
- **放弃原因**：TypeScript生态优势明显

### 备选方案B：完全重写Python工具
- **优点**：代码库统一为TypeScript
- **缺点**：
  - 增加开发时间（需重写5个工具）
  - 引入新bug风险
  - v0.1.0测试需重跑
- **放弃原因**：Python工具已稳定，无需重写

### 备选方案C：微服务架构（Python + TypeScript分离）
- **优点**：完全解耦，可独立部署
- **缺点**：
  - 增加运维复杂度
  - 网络开销
  - 过度设计（当前规模不需要）
- **放弃原因**：Monorepo足够，未来可升级

## 后果

### 正面影响
1. **功能大幅提升**
   - 完整的7节点编排流程
   - 知识图谱支持（NervusDB）
   - 自动引用追踪（Search Grounding）
   - 生产级可观测性

2. **质量保证**
   - 完整的测试覆盖（单元/集成/E2E）
   - CI/CD自动化
   - Prompt版本管理

3. **可扩展性**
   - pnpm workspace便于添加新包
   - 插件化架构（adapters/）
   - 支持批处理和优先级队列

4. **开发体验**
   - TypeScript类型安全
   - Orion经验可直接复用
   - 丰富的生态工具（vitest/tsup）

### 负面影响
1. **技术栈复杂度**
   - 需要维护Python + TypeScript
   - 团队需要TypeScript技能
   - **缓解**：Python工具保持简单，核心逻辑在TS

2. **迁移成本**
   - v0.1.0用户需要重新安装依赖（pnpm）
   - CLI命令行为可能微调
   - **缓解**：提供详细迁移指南，保持向后兼容

3. **调试复杂度**
   - Python ↔ TypeScript 跨语言调试
   - **缓解**：完善日志系统，子进程错误传播清晰

## 实施计划

### Milestone: v0.2.0（预计4周）

**Week 1: 架构和基础**
- [ ] Issue #12: ADR文档（本文档）
- [ ] Issue #13: TypeScript项目初始化
- [ ] Issue #14: LangGraph编排核心

**Week 2: 适配器**
- [ ] Issue #15: Gemini适配器
- [ ] Issue #16: NervusDB集成
- [ ] Python工具桥接

**Week 3: CLI和测试**
- [ ] Issue #17: CLI迁移
- [ ] Issue #20: 端到端测试

**Week 4: 质量和文档**
- [ ] Issue #18: 可观测性
- [ ] Issue #19: Prompt治理
- [ ] 更新文档和示例

### 验收标准
1. **功能完整**
   - 7节点编排流程可用
   - NervusDB查询正常
   - Search Grounding返回引用

2. **质量达标**
   - 测试覆盖率>70%
   - CI全绿
   - E2E测试通过

3. **文档完善**
   - 迁移指南
   - API文档
   - 架构图

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| TypeScript学习曲线 | 中 | 中 | 参考Orion代码，渐进式学习 |
| Python桥接不稳定 | 低 | 高 | 完善错误处理，添加重试机制 |
| NervusDB性能问题 | 低 | 中 | 保持缓存层简单，可回退到Python |
| 迁移破坏用户体验 | 中 | 高 | 提供v0.1.0 → v0.2.0迁移脚本 |

## 参考资料

- [Orion项目](https://github.com/persomsad/Orion)
- [ADR-001: CLI Agent架构](./ADR-001-cli-agent-architecture.md)
- [LangGraph官方文档](https://langchain-ai.github.io/langgraph/)
- [@google/genai SDK](https://ai.google.dev/gemini-api/docs)
- [NervusDB文档](https://github.com/nervusdb/nervusdb)

## 变更记录
- v1 - 2025-11-09：初始架构设计，定义混合架构方案
