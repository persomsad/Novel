# 下一步优化建议

**生成时间**: 2025-11-09
**当前版本**: v0.2.0-dev
**目标**: 成为"小说创作界的 Claude Code"

---

## ✅ 已完成 (v0.2.0)

### P0 功能（核心体验）
- ✅ **精准编辑工具** (commit: 1d724c8)
  - `edit_chapter_lines()`: 修改章节指定行
  - `replace_in_file()`: 查找替换文本
  - `multi_edit()`: 批量编辑多个文件（原子性）

- ✅ **自动修复建议** (commit: 1d724c8)
  - `verify_strict_timeline()`: 返回结构化错误 + 修复建议
  - `verify_strict_references()`: 返回结构化错误 + 修复建议

- ✅ **智能图查询** (commit: 70eb865)
  - `smart_context_search()`: 多跳图遍历 + 置信度评分
  - `build_character_network()`: 角色关系网络 + 社区检测
  - `trace_foreshadow()`: 伏笔链条追溯

### 测试覆盖率
- 从 14% → **68%**
- 125 个测试全部通过

---

## 🎯 接下来应该做什么？

根据 `docs/analysis-gap-to-claude-code.md` 分析，**还剩 1 个 P0 功能**：

### P0-4: 实时上下文理解 ⭐⭐⭐⭐⭐

**现状问题：**
- ❌ Agent 需要自己搜索相关信息（"帮我读取角色设定"）
- ❌ 上下文索引需要手动刷新（`refresh-memory`）
- ❌ 无法自动感知文件变更

**目标：**
Agent 自动选择相关上下文，像 Claude Code 一样智能：
```
用户："检查第3章的角色一致性"
Agent: [自动加载]
  - spec/knowledge/character-profiles.md (角色设定)
  - chapters/ch003.md (当前章节)
  - chapters/ch001-002.md (前置章节，用于对比)
[开始推理...]
```

**核心技术：图数据库 + ripgrep（学习 Claude Code）**
- ✅ 精确匹配，不会有语义偏差
- ✅ 零延迟，不需要 Embedding 模型
- ✅ 零成本，不需要额外依赖
- ✅ 可解释性强，用户能理解为什么匹配

**实现方案：**

#### 1. 文件监控 + 自动刷新索引 (2-3天)

```python
# 新增模块: src/novel_agent/file_watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NovelFileHandler(FileSystemEventHandler):
    """监控章节和设定文件变更"""

    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            # 自动增量更新索引
            update_continuity_index(event.src_path)

# 启动监控（daemon模式）
observer = Observer()
observer.schedule(handler, path='chapters/', recursive=True)
observer.schedule(handler, path='spec/', recursive=True)
observer.start()
```

**依赖：** `watchdog>=4.0.0`

#### 2. 智能上下文检索器 (2-3天)

```python
# 新增模块: src/novel_agent/context_retriever.py
class ContextRetriever:
    """基于图数据库 + grep 文本搜索的混合检索

    灵感来源：Claude Code 使用 ripgrep 而非向量检索
    优势：精确、快速、零成本、可解释
    """

    def retrieve_context(
        self,
        query: str,
        max_tokens: int = 10000
    ) -> list[Document]:
        """智能选择相关文档

        策略（按优先级）：
        1. 图查询：从 NervusDB 找出直接关联的实体
        2. 文本搜索：用 ripgrep 找包含关键词的文档
        3. 时间线过滤：只返回相关时间段的章节
        4. 优先级排序：章节 > 设定 > 大纲
        """

        # 1. 从 NervusDB 图查询相关实体
        entities = self.graph_query(query)

        # 2. 获取实体关联的文档（通过图关系）
        docs_by_graph = self.get_documents_by_entities(entities)

        # 3. 文本搜索补充（ripgrep 精确匹配）
        docs_by_grep = self.grep_search(query)

        # 4. 合并去重 + 优先级排序
        return self.merge_and_rank(docs_by_graph, docs_by_grep)
```

**依赖：**
- 无新增依赖！已有 ripgrep 和 NervusDB

#### 3. Agent 自动上下文注入 (1-2天)

```python
# 修改: src/novel_agent/agent.py
def create_novel_agent(...):
    # 添加上下文检索器
    retriever = ContextRetriever(
        graph_db="data/novel-graph.nervusdb",
        index_path="data/continuity/index.json"
    )

    # 在每次对话前自动注入上下文
    def inject_context(state: AgentState) -> AgentState:
        query = state["messages"][-1].content
        context_docs = retriever.retrieve_context(query)

        # 将上下文添加到 system message
        context_text = "\n\n".join([
            f"## {doc.metadata['source']}\n{doc.page_content}"
            for doc in context_docs
        ])

        state["context"] = context_text
        return state

    # 添加到 LangGraph workflow
    workflow.add_node("inject_context", inject_context)
    workflow.add_edge(START, "inject_context")
    workflow.add_edge("inject_context", "agent")
```

---

## 📊 优先级总结

### 立即实施（本周）⭐⭐⭐⭐⭐
1. **实时上下文理解** (P0-4)
   - 工作量：5-6 天（去掉向量后更快）
   - 价值：Agent 智能度提升 10 倍
   - 依赖：watchdog（仅此一个！）

### 下一版本（v0.3.0）
2. **VSCode 插件** (P1)
   - 工作量：2-3 周
   - 价值：编辑器集成，用户体验质变
   - 参考：Gemini CLI 的 vscode-ide-companion

3. **Agent 记忆系统增强** (P1)
   - 工作量：1 周
   - 价值：长期对话上下文保持
   - 技术：LangGraph Checkpointer + 向量检索

### 长期规划（v0.4.0+）
4. **多模态支持** (P2)
   - 图片理解（角色设计图）
   - 语音输入输出

5. **协作功能** (P2)
   - 多人实时编辑
   - 评论和建议系统

---

## 🚀 实施路线图

### Week 1: 实时上下文理解（5-6天）
```bash
# Day 1-2: 文件监控
- 安装 watchdog
- 实现 file_watcher.py
- 集成到 CLI (daemon 模式)

# Day 3-5: 智能检索（图 + grep）
- 实现 ContextRetriever
- 集成 NervusDB 图查询
- 集成 ripgrep 文本搜索
- 优先级排序算法

# Day 6: Agent 集成 + 测试
- 修改 agent.py 注入上下文
- 测试和优化
- 文档更新
```

### Week 3-5: VSCode 插件
```bash
# Week 3: 基础架构
- VSCode Extension 项目搭建
- WebSocket 服务器（连接 Agent）
- 右键菜单集成

# Week 4: 核心功能
- 侧边栏：角色列表、时间线
- Inline Diff 预览
- 实时一致性检查

# Week 5: 发布
- 测试和文档
- VSCode Marketplace 发布
```

---

## 💡 技术决策

### 为什么优先实时上下文理解？

| 功能 | 价值 | 复杂度 | ROI |
|------|------|--------|-----|
| 实时上下文 | ⭐⭐⭐⭐⭐ | 🔧🔧🔧 | **最高** |
| VSCode 插件 | ⭐⭐⭐⭐ | 🔧🔧🔧🔧 | 高 |
| 多模态 | ⭐⭐⭐ | 🔧🔧🔧🔧🔧 | 低 |

**原因：**
1. **痛点最大**: 用户最常抱怨"Agent 记不住设定"
2. **技术成熟**: 图数据库 + 向量检索已有成熟方案
3. **快速见效**: 10 天内可完成，立即提升体验

### 为什么不先做 VSCode 插件？

**风险：**
- 编辑器集成需要 2-3 周，时间长
- 如果 Agent 核心能力不够强，插件也没用
- VSCode API 学习成本高

**策略：**
- 先让 Agent 变聪明（实时上下文）
- 再包装到编辑器里

---

## 📝 执行检查清单

### 开始实时上下文理解前的准备

- [ ] 阅读 `docs/analysis-gap-to-claude-code.md` 完整分析
- [ ] 安装依赖：`poetry add watchdog sentence-transformers`
- [ ] 创建新分支：`git checkout -b feat/realtime-context`
- [ ] 创建设计文档：`docs/architecture/ADR-004-realtime-context.md`
- [ ] 创建测试计划：`tests/test_context_retriever.py`

### 完成标准

- [ ] 文件修改自动触发索引更新（延迟 < 1秒）
- [ ] Agent 自动选择相关上下文（准确率 > 80%）
- [ ] 上下文注入不影响性能（延迟 < 500ms）
- [ ] 测试覆盖率保持 > 60%
- [ ] 文档更新完成

---

## 🤔 需要决策的问题

### 1. 为什么不用向量检索？✅ 已决策

**方案：图 + grep（学习 Claude Code）**

Claude Code 的实践证明：
- ✅ **ripgrep 足够精确**：全文搜索比语义相似度更可靠
- ✅ **零延迟**：不需要 Embedding 模型（200MB+）
- ✅ **零成本**：不需要向量数据库和维护
- ✅ **可解释**：用户能理解为什么匹配

**我们的方案比 Claude Code 更强**：
- Claude Code: 仅 grep
- 我们: **图数据库 + grep** = 精确关系 + 文本搜索

### 2. 实时监控 vs 手动刷新？

**方案 A: 自动监控（watchdog）**
- ✅ 用户无感知，体验好
- ❌ 后台进程，占用资源

**方案 B: 保持手动刷新**
- ✅ 简单可控
- ❌ 用户需要记得刷新

**建议**: 实现方案 A，但提供开关（默认开启）

---

## 📚 参考资料

- [watchdog 文档](https://python-watchdog.readthedocs.io/)
- [sentence-transformers 文档](https://www.sbert.net/)
- [LangChain Context Retrieval](https://python.langchain.com/docs/modules/data_connection/)
- [Gemini CLI vscode-ide-companion](https://github.com/google-gemini/gemini-cli/tree/main/vscode-ide-companion)
- [Claude Code 架构分析](https://docs.anthropic.com/claude/docs/about-claude-for-vscode)

---

**下一步行动**: 创建 `feat/realtime-context` 分支，开始实现文件监控模块。
