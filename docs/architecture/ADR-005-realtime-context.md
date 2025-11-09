# ADR-005: 实时上下文理解与自动注入

## 元信息
- 创建：2025-11-09
- 最近一次更新：2025-11-09
- 状态：active
- 版本：v1

## 背景

### 当前问题

**用户痛点**：
```
用户："检查第3章的角色一致性"
Agent："好的，请告诉我角色设定在哪个文件"
用户："在 spec/knowledge/character-profiles.md"
Agent："好的，请告诉我第3章的路径"
用户："chapters/ch003.md" 😤
```

**核心问题**：
1. ❌ Agent 需要用户手动指定相关文件
2. ❌ 上下文索引需要手动刷新（`refresh-memory`）
3. ❌ 无法自动感知文件变更
4. ❌ 用户体验差，远不如 Claude Code

**对标目标：Claude Code**
- ✅ 自动理解代码库结构
- ✅ 自动选择相关上下文
- ✅ 实时跟踪文件变更
- ✅ 零配置，开箱即用

### 需求

**目标用户体验**：
```
用户："检查第3章的角色一致性"
Agent: [自动加载]
  ✅ spec/knowledge/character-profiles.md (角色设定)
  ✅ chapters/ch003.md (当前章节)
  ✅ chapters/ch001-002.md (前置章节，用于对比)
[开始推理...]
✓ 发现1个问题：主角性格在第3章与设定不一致...
```

**功能需求**：
1. 实时监控文件变更 → 自动更新索引
2. 智能选择相关上下文 → 无需用户指定
3. 自动注入到 Agent → 零配置

---

## 决策

### 核心方案：图数据库 + grep（学习 Claude Code）

**技术选型：**

| 组件 | 技术 | 理由 |
|------|------|------|
| 文件监控 | watchdog | Python 生态标准，跨平台 |
| 实体查询 | NervusDB 图 | 精确关系推理（角色、地点、伏笔） |
| 文本搜索 | ripgrep | Claude Code 同款，精确快速 |
| 索引存储 | JSON + SQLite | 轻量级，易调试 |

**为什么不用向量检索？**

Claude Code 的实践证明：
- ✅ **ripgrep 足够精确**：全文搜索比语义相似度更可靠
- ✅ **零延迟**：不需要 Embedding 模型（200MB+）
- ✅ **零成本**：不需要向量数据库和维护
- ✅ **可解释**：用户能理解为什么匹配

**我们的优势（vs Claude Code）**：
- Claude Code: 仅 grep
- Novel Agent: **图 + grep** = 精确关系 + 文本搜索

---

## 架构设计

### 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    用户输入                          │
│         "检查第3章的角色一致性"                      │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              Context Retriever                       │
│              （智能上下文检索器）                    │
│                                                      │
│  ┌─────────────┐      ┌──────────────┐             │
│  │ NervusDB 图 │─────▶│ 实体查询     │             │
│  │ 角色/地点等 │      │ characters   │             │
│  └─────────────┘      │ locations    │             │
│                       │ foreshadows  │             │
│                       └──────┬───────┘             │
│                              │                      │
│                              ▼                      │
│                       ┌──────────────┐             │
│                       │ 文档映射     │             │
│                       │ entity→files │             │
│                       └──────┬───────┘             │
│                              │                      │
│  ┌─────────────┐             │                      │
│  │ ripgrep     │─────────────┤                      │
│  │ 文本搜索    │             │                      │
│  └─────────────┘             │                      │
│                              ▼                      │
│                       ┌──────────────┐             │
│                       │ 合并排序     │             │
│                       │ priority     │             │
│                       │ ranking      │             │
│                       └──────┬───────┘             │
└───────────────────────────────┼─────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────┐
│              Context Injection                       │
│              （上下文注入）                          │
│                                                      │
│  ┌─────────────┐      ┌──────────────┐             │
│  │ 格式化上下文 │─────▶│ 注入 system  │             │
│  │ 限制 token   │      │ message      │             │
│  └─────────────┘      └──────────────┘             │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│                   ReAct Agent                        │
│              （带上下文的推理）                      │
└─────────────────────────────────────────────────────┘
```

### 文件监控

```python
# src/novel_agent/file_watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NovelFileHandler(FileSystemEventHandler):
    """监控 chapters/ 和 spec/ 文件变更"""

    def __init__(self, index_updater):
        self.index_updater = index_updater

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.md'):
            return

        # 自动增量更新索引
        self.index_updater.update_file(event.src_path)

    def on_created(self, event):
        self.on_modified(event)

    def on_deleted(self, event):
        if event.src_path.endswith('.md'):
            self.index_updater.remove_file(event.src_path)

# 启动监控（daemon模式）
def start_file_watcher(chapters_dir, spec_dir):
    observer = Observer()
    handler = NovelFileHandler(index_updater)
    observer.schedule(handler, chapters_dir, recursive=True)
    observer.schedule(handler, spec_dir, recursive=True)
    observer.start()
    return observer
```

### 智能检索器

```python
# src/novel_agent/context_retriever.py
from pathlib import Path
import subprocess
from typing import List

class ContextRetriever:
    """基于图 + grep 的智能上下文检索"""

    def __init__(self, graph_db_path: str, index_path: str):
        self.graph_querier = GraphQuerier(graph_db_path)
        self.index = load_index(index_path)

    def retrieve_context(
        self,
        query: str,
        max_tokens: int = 10000
    ) -> List[Document]:
        """智能选择相关文档

        策略：
        1. 图查询：从 NervusDB 找出直接关联的实体
        2. 文本搜索：用 ripgrep 找包含关键词的文档
        3. 时间线过滤：只返回相关时间段的章节
        4. 优先级排序：章节 > 设定 > 大纲
        """

        # 1. 从图中提取实体
        entities = self._extract_entities(query)

        # 2. 图查询：找相关文档
        docs_by_graph = self._query_by_graph(entities)

        # 3. grep 搜索：文本匹配
        docs_by_grep = self._grep_search(query)

        # 4. 合并去重
        all_docs = self._merge_documents(docs_by_graph, docs_by_grep)

        # 5. 优先级排序
        ranked_docs = self._rank_documents(all_docs, query)

        # 6. Token 限制
        return self._limit_tokens(ranked_docs, max_tokens)

    def _extract_entities(self, query: str) -> List[str]:
        """从查询中提取实体名（角色、地点等）"""
        # 简单实现：从索引中匹配
        entities = []
        for char in self.index['characters']:
            if char['name'] in query:
                entities.append(('character', char['name']))
        # 类似处理 locations, events 等
        return entities

    def _query_by_graph(self, entities: List[tuple]) -> List[Document]:
        """通过图查询相关文档"""
        docs = []
        for entity_type, entity_name in entities:
            # 从图中找这个实体出现的所有章节
            result = self.graph_querier.smart_context_search(
                query=entity_name,
                search_type=entity_type,
                max_hops=1
            )

            # 转换为 Document
            for item in result['results']:
                if 'chapters' in item:
                    for chapter in item['chapters']:
                        docs.append(Document(
                            path=f"chapters/ch{chapter:03d}.md",
                            source='graph',
                            confidence=item['confidence']
                        ))

        return docs

    def _grep_search(self, query: str) -> List[Document]:
        """使用 ripgrep 搜索文本"""
        try:
            # 使用 rg 搜索
            result = subprocess.run(
                ['rg', '--json', '--max-count=5', query,
                 'chapters/', 'spec/'],
                capture_output=True,
                text=True,
                timeout=5
            )

            docs = []
            for line in result.stdout.splitlines():
                match = json.loads(line)
                if match['type'] == 'match':
                    docs.append(Document(
                        path=match['data']['path']['text'],
                        source='grep',
                        confidence=0.8,
                        context=match['data']['lines']['text']
                    ))

            return docs
        except Exception as e:
            logger.warning(f"grep 搜索失败: {e}")
            return []

    def _rank_documents(self, docs: List[Document], query: str) -> List[Document]:
        """优先级排序"""
        def priority_score(doc: Document) -> float:
            score = doc.confidence

            # 文件类型优先级
            if 'chapters/' in doc.path:
                score += 1.0  # 章节优先
            elif 'spec/knowledge/' in doc.path:
                score += 0.8  # 设定次之
            elif 'spec/outline.md' in doc.path:
                score += 0.5  # 大纲最后

            # 来源优先级
            if doc.source == 'graph':
                score += 0.2  # 图查询更精确

            return score

        return sorted(docs, key=priority_score, reverse=True)
```

### Agent 集成

```python
# src/novel_agent/agent.py (修改)
def create_novel_agent(...):
    # 初始化上下文检索器
    retriever = ContextRetriever(
        graph_db_path="data/novel-graph.nervusdb",
        index_path="data/continuity/index.json"
    )

    # 添加上下文注入节点
    def inject_context(state: AgentState) -> AgentState:
        """在每次对话前自动注入相关上下文"""
        query = state["messages"][-1].content

        # 智能检索上下文
        context_docs = retriever.retrieve_context(query)

        # 格式化为文本
        context_text = "\n\n".join([
            f"## {doc.path}\n```\n{doc.content[:500]}...\n```"
            for doc in context_docs
        ])

        # 注入到 state
        state["context"] = context_text
        state["context_files"] = [doc.path for doc in context_docs]

        return state

    # 修改 system prompt
    enhanced_prompt = config["system_prompt"] + """

## 自动上下文（已为你加载）

以下是与当前对话相关的文档，你可以直接引用：

{context}

**注意**：这些文档是自动选择的，包含与用户查询最相关的内容。
"""

    # 添加到 workflow
    workflow = StateGraph(AgentState)
    workflow.add_node("inject_context", inject_context)
    workflow.add_node("agent", agent_node)

    workflow.add_edge(START, "inject_context")
    workflow.add_edge("inject_context", "agent")
    workflow.add_edge("agent", END)

    return workflow.compile()
```

---

## 备选方案

### 备选方案 A：向量检索

**技术**：sentence-transformers + chromadb

**优点**：
- 语义相似度匹配
- 可以找到"意思相近"的文档

**缺点**：
- 需要 200MB+ Embedding 模型
- 延迟高（500ms+）
- 语义偏差（"张三的朋友" 可能匹配到无关内容）
- 黑盒，用户无法理解匹配原因

**放弃原因**：Claude Code 已证明 grep 更可靠

### 备选方案 B：手动指定上下文

**技术**：保持现状，用户手动指定文件

**优点**：
- 简单，无需额外实现
- 用户完全控制

**缺点**：
- 用户体验差
- 无法对标 Claude Code
- 用户容易遗漏相关文档

**放弃原因**：不符合"智能助手"定位

---

## 后果

### 正面

1. **用户体验质变**
   - 无需手动指定文件
   - 无需手动刷新索引
   - 像 Claude Code 一样智能

2. **Agent 能力提升**
   - 自动获取完整上下文
   - 推理更准确
   - 错误率降低

3. **技术优势**
   - 比 Claude Code 更强（图 + grep > 单纯 grep）
   - 零额外成本（无需 Embedding 模型）
   - 可解释性强

### 负面

1. **后台进程**
   - watchdog 需要后台运行
   - 占用少量资源（<50MB）
   - **缓解措施**：提供开关，默认开启

2. **初始索引耗时**
   - 首次启动需要构建索引
   - 大型项目（100+章节）可能需要 10-30秒
   - **缓解措施**：异步构建，显示进度

3. **索引一致性**
   - 如果 watchdog 未运行，索引可能过期
   - **缓解措施**：检测索引过期，自动重建

---

## 跟进与验证

### 实现计划

- [x] 安装 watchdog 依赖
- [ ] Day 1-2: 实现 file_watcher.py
  - [ ] 基础文件监控
  - [ ] 增量索引更新
  - [ ] Daemon 模式集成
- [ ] Day 3-5: 实现 context_retriever.py
  - [ ] 实体提取
  - [ ] 图查询集成
  - [ ] grep 搜索集成
  - [ ] 优先级排序
- [ ] Day 6: Agent 集成
  - [ ] 修改 agent.py
  - [ ] 测试端到端流程
  - [ ] 性能优化

### 验证标准

**功能验证**：
- [ ] 文件修改 1 秒内触发索引更新
- [ ] 上下文检索准确率 > 80%
- [ ] 端到端延迟 < 500ms

**性能验证**：
- [ ] watchdog 内存占用 < 50MB
- [ ] 索引更新延迟 < 1s
- [ ] 检索延迟 < 200ms

**用户体验验证**：
- [ ] 无需手动指定文件
- [ ] 自动选择相关上下文
- [ ] 对话流畅，无明显卡顿

### 回滚计划

如果验证失败：
1. 回滚到 main 分支
2. watchdog 可以卸载（无副作用）
3. 保留设计文档，供后续优化

---

## 变更记录

- v1 - 2025-11-09：初始决策，确定图+grep方案
