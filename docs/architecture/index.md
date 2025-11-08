# Architecture Decision Records (ADR) Index

本目录记录了 Novel Agent 项目的所有重要技术决策。

## 什么是 ADR？

ADR (Architecture Decision Record) 是记录软件架构决策的文档格式。每个 ADR 描述一个重要决策，包括：
- 背景和问题
- 考虑的方案
- 最终决策
- 决策的后果

## ADR 列表

| 编号 | 标题 | 状态 | 最后更新 | 相关 Issue |
|------|------|------|----------|-----------|
| [ADR-001](./ADR-001-cli-agent-architecture.md) | CLI Agent 技术方案 | Active | 2025-11-08 | #1, #2, #3, #4 |
| [ADR-002](./ADR-002-Orion-Integration.md) | Orion架构集成方案 | Active | 2025-11-09 | #12, #13, #14 |

## ADR 状态说明

- **Draft**: 草稿，待讨论
- **Active**: 已采纳并实施
- **Superseded**: 已被新的 ADR 替代
- **Deprecated**: 已废弃

## 如何编写 ADR

### 1. 创建新的 ADR

```bash
# 使用下一个编号
cp ADR-template.md ADR-00X-title.md
```

### 2. ADR 模板结构

```markdown
# ADR-00X: 决策标题

## 元信息
- 创建：YYYY-MM-DD
- 最后更新：YYYY-MM-DD
- 状态：Draft/Active/Superseded/Deprecated
- 相关 Issue：#X, #Y

## 背景
描述触发此决策的问题或需求

## 决策
说明最终采用的方案

## 备选方案
列出考虑过的其他方案及其优缺点

## 后果
描述此决策的正面和负面影响

## 实施
如何实施此决策（可选）
```

### 3. 更新索引

在 `index.md` 中添加新的 ADR 记录。

## 决策原则

### 1. 简单优先
> "简单是终极的复杂" - 达芬奇

- 优先选择简单的方案
- 避免过度设计
- 保持代码和架构的简洁性

### 2. 实用主义
> "不解决假想的问题，只解决真实的问题" - Linus Torvalds

- 基于实际需求做决策
- 避免为未来可能永远不会出现的需求设计
- YAGNI (You Aren't Gonna Need It)

### 3. 数据驱动
> "Bad programmers worry about the code. Good programmers worry about data structures and their relationships." - Linus Torvalds

- 先设计数据结构
- 代码围绕数据组织
- 好的数据结构让算法自然涌现

### 4. 可测试性
- 设计必须可测试
- 测试覆盖率 >50%
- 端到端测试验证核心功能

### 5. 文档化
- 重要决策必须记录 ADR
- 代码注释解释"为什么"，不是"做什么"
- README 保持更新

## 相关资源

- [ADR GitHub](https://adr.github.io/)
- [Thoughtworks ADR Tools](https://github.com/npryce/adr-tools)
- [When Should I Write an ADR?](https://engineering.atspotify.com/2020/04/when-should-i-write-an-architecture-decision-record/)

## 变更历史

- 2025-11-09: 添加 ADR-002 (Orion架构集成)
- 2025-11-08: 创建 ADR 索引
- 2025-11-08: 添加 ADR-001 (CLI Agent 架构)
