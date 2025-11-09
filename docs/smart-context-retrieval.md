# 智能上下文检索方案（基于 NervusDB 图数据库）

> **"向量检索是弟弟，图数据库才是王道"** - 小说场景的真理

## 1. 核心理念

### 为什么图 > 向量？

| 维度 | 向量检索 (Embedding) | 图数据库 (NervusDB) |
|------|---------------------|---------------------|
| **关系表达** | ❌ 语义相似度（单维度） | ✅ 多种关系（角色、地点、时间、伏笔、因果） |
| **时间感知** | ❌ 无法处理时间先后 | ✅ 原生时间线 (TemporalStore) |
| **精准定位** | ❌ 近似匹配（可能漏） | ✅ 精确图遍历（保证完整） |
| **复杂查询** | ❌ 只能简单相似度 | ✅ Cypher 多跳路径查询 |
| **可解释性** | ❌ 黑盒（为什么推荐？） | ✅ 清晰路径（通过XX关系找到） |
| **成本** | 💰 API 调用费用 | 🆓 本地嵌入式（零成本） |

### 小说场景的关键需求

1. **角色关系网络**：谁认识谁、谁爱谁、谁杀了谁
2. **时间线追溯**：事件 A 发生在事件 B 之前/之后
3. **伏笔关联**：第 5 章埋的伏笔在第 20 章揭晓
4. **地点共现**：哪些角色在同一地点出现过
5. **因果推理**：因为 X 发生，所以 Y 发生

**结论**：这些需求都是**图结构**，用向量检索是削足适履！

---

## 2. NervusDB 核心能力

### 2.1 三元组存储（SPO）

```typescript
// 基础 Fact: Subject - Predicate -> Object
await db.insertFact({
  subject: 'alice',
  predicate: 'knows',
  object: 'bob',
  properties: { since: 2021, strength: 0.9 }
});

// 查询
const results = await db.query()
  .anchor('alice')
  .out('knows')
  .withProperty('since', (v) => v >= 2020)
  .all();
```

### 2.2 时间线查询 (TemporalStore)

```typescript
// 记录事件
const episode = await db.temporal.addEpisode({
  source_type: 'chapter',
  payload: { chapter: 3, content: '...' },
  occurred_at: '2024-01-15T10:00:00Z'
});

// 查询时间线
const timeline = db.temporal.timeline({
  entity_id: alice_id,
  predicate_key: 'meets',
  role: 'subject',
  between: ['2024-01-01T00:00:00Z', '2024-01-31T23:59:59Z']
});

// 追溯 Fact 来源
const episodes = db.temporal.traceBack(fact_id);
```

### 2.3 高级查询 (Cypher)

```cypher
// 找出所有通过"中间人"认识的人
MATCH (a:Person)-[:knows]->(m:Person)-[:knows]->(b:Person)
WHERE a.name = 'alice' AND a <> b
RETURN DISTINCT b.name, m.name AS via

// 找出最短路径
MATCH path = shortestPath((a:Person)-[:knows*]-(b:Person))
WHERE a.name = 'alice' AND b.name = 'charlie'
RETURN path

// 时间约束查询
MATCH (a:Person)-[r:meets]->(b:Person)
WHERE r.timestamp > '2024-01-01' AND r.timestamp < '2024-01-31'
RETURN a.name, b.name, r.timestamp
ORDER BY r.timestamp
```

### 2.4 图算法 (Extensions)

```typescript
import { Extensions } from '@nervusdb/core';

// 中心性分析（找出最重要角色）
const central = Extensions.Algorithms.centrality.betweenness(db);

// 社区检测（角色分组）
const communities = Extensions.Algorithms.community.louvain(db);

// 相似度计算
const similar = Extensions.Algorithms.similarity.jaccard(
  'alice_neighbors',
  'bob_neighbors'
);
```

---

## 3. 智能上下文检索设计

### 3.1 数据模型

#### 节点类型 (Labels)

```typescript
// 角色
{ label: 'Character', properties: { name, gender, age, personality } }

// 地点
{ label: 'Location', properties: { name, type, description } }

// 章节
{ label: 'Chapter', properties: { number, title, word_count } }

// 情节事件
{ label: 'Event', properties: { description, chapter, timestamp } }

// 伏笔
{ label: 'Foreshadow', properties: { id, setup_chapter, reveal_chapter } }
```

#### 关系类型 (Predicates)

```typescript
// 角色关系
'knows', 'loves', 'hates', 'kills', 'father_of', 'mentor_of'

// 地点关系
'located_in', 'travels_to', 'appears_in'

// 事件关系
'causes', 'precedes', 'triggers', 'resolves'

// 章节关系
'contains_character', 'contains_event', 'mentions', 'follows'

// 伏笔关系
'foreshadows', 'fulfills', 'related_to'
```

### 3.2 核心检索能力

#### 能力 1：角色关系检索

**场景**：用户提到"张三"，需要找出所有相关章节

**查询**：
```cypher
// 1. 直接出现
MATCH (c:Chapter)-[:contains_character]->(char:Character {name: '张三'})
RETURN c.number, c.title

// 2. 通过关系关联（朋友、敌人）
MATCH (char:Character {name: '张三'})-[:knows|loves|hates]-(other:Character)
      <-[:contains_character]-(c:Chapter)
RETURN c.number, other.name AS related_via

// 3. 多跳关系（张三 -> 李四 -> 王五出现的章节）
MATCH (char:Character {name: '张三'})-[:knows*1..2]-(other:Character)
      <-[:contains_character]-(c:Chapter)
RETURN c.number, other.name, length(path) AS hops
ORDER BY hops ASC
```

#### 能力 2：时间线检索

**场景**：找出某个时间段内的所有事件

**查询**：
```typescript
// 使用 NervusDB 原生 TemporalStore
const events = db.temporal.timeline({
  entity_id: character_id,
  predicate_key: 'participates_in',
  between: [start_time, end_time]
});

// 或者 Cypher 查询
const results = await db.cypher(`
  MATCH (char:Character {name: '张三'})-[:participates_in]->(event:Event)
  WHERE event.timestamp >= $start AND event.timestamp <= $end
  RETURN event.description, event.chapter
  ORDER BY event.timestamp
`, { start, end });
```

#### 能力 3：伏笔追溯

**场景**：某个伏笔在哪里埋下，在哪里揭晓

**查询**：
```cypher
// 查找伏笔链
MATCH (setup:Chapter)-[:contains]->(f:Foreshadow)-[:fulfills]->(reveal:Chapter)
WHERE f.id = 'foreshadow_001'
RETURN setup.number AS setup_chapter,
       reveal.number AS reveal_chapter,
       f.description

// 查找未解伏笔
MATCH (c:Chapter)-[:contains]->(f:Foreshadow)
WHERE NOT exists((f)-[:fulfills]->())
RETURN c.number, f.id, f.description
```

#### 能力 4：地点共现

**场景**：找出在同一地点出现过的所有角色

**查询**：
```cypher
// 在同一地点出现的角色
MATCH (loc:Location {name: '天安门'})<-[:appears_in]-(char:Character)
RETURN char.name

// 同时出现在某地点的角色组合
MATCH (char1:Character)-[:appears_in]->(loc:Location)<-[:appears_in]-(char2:Character)
WHERE char1.name < char2.name  // 避免重复
RETURN loc.name, char1.name, char2.name
```

#### 能力 5：因果推理

**场景**：事件 X 导致了哪些后续事件

**查询**：
```cypher
// 直接因果
MATCH (e1:Event {id: 'event_001'})-[:causes]->(e2:Event)
RETURN e2.description, e2.chapter

// 多级因果链
MATCH path = (e1:Event {id: 'event_001'})-[:causes*1..3]->(e:Event)
RETURN e.description, length(path) AS depth
ORDER BY depth ASC
```

---

## 4. 实现方案

### 4.1 工具设计

#### Tool 1: `smart_context_search`

**功能**：智能搜索相关上下文

**参数**：
```python
def smart_context_search(
    query: str,              # 用户查询（如"张三和李四的关系"）
    search_type: str,        # 'character' | 'location' | 'event' | 'foreshadow' | 'all'
    max_hops: int = 2,       # 最大关系跳数
    time_range: tuple = None,# 时间范围 (start, end)
    limit: int = 10          # 最多返回条数
) -> dict:
    """
    Returns:
    {
        "results": [
            {
                "type": "chapter",
                "chapter_number": 5,
                "relevance": "contains_character",
                "path": ["张三", "knows", "李四", "appears_in", "ch005"],
                "excerpt": "...",
                "metadata": { "timestamp": "...", "confidence": 0.9 }
            },
            ...
        ],
        "summary": "找到 10 个相关章节，主要通过 'knows' 关系关联",
        "graph_stats": {
            "nodes_searched": 50,
            "edges_traversed": 120,
            "max_depth": 3
        }
    }
    """
```

#### Tool 2: `build_character_network`

**功能**：构建角色关系网络图

**输出**：
```json
{
  "nodes": [
    { "id": "alice", "label": "Alice", "type": "protagonist" },
    { "id": "bob", "label": "Bob", "type": "supporting" }
  ],
  "edges": [
    { "source": "alice", "target": "bob", "relation": "knows", "weight": 0.9 }
  ],
  "clusters": [
    { "id": 1, "members": ["alice", "bob", "charlie"], "label": "主角团" }
  ]
}
```

#### Tool 3: `trace_foreshadow`

**功能**：追溯伏笔完整链条

**输出**：
```json
{
  "foreshadow_id": "foreshadow_001",
  "setup": {
    "chapter": 5,
    "line": 120,
    "text": "张三神秘地笑了笑，没有回答"
  },
  "hints": [
    { "chapter": 8, "type": "implicit", "text": "..." },
    { "chapter": 12, "type": "explicit", "text": "..." }
  ],
  "reveal": {
    "chapter": 20,
    "line": 340,
    "text": "原来张三就是幕后黑手！"
  },
  "related_events": [
    { "chapter": 7, "event": "王五失踪" }
  ]
}
```

### 4.2 数据摄取流程

#### 自动解析章节并构建图

```python
def ingest_chapter(chapter_path: str):
    """
    1. 读取章节内容
    2. 提取实体（角色、地点、事件）
    3. 识别关系（谁和谁互动、在哪里）
    4. 时间标记（如果有日期/时间）
    5. 写入 NervusDB
    """
    content = read_file(chapter_path)
    entities = extract_entities(content)  # NER
    relations = extract_relations(content) # RE

    for entity in entities:
        db.insertFact({
            'subject': f'ch{chapter_num}',
            'predicate': 'contains_character',
            'object': entity.name
        })

    for rel in relations:
        db.insertFact({
            'subject': rel.source,
            'predicate': rel.type,
            'object': rel.target,
            'properties': { 'chapter': chapter_num, ... }
        })
```

#### 增量更新

```python
def refresh_context_graph():
    """
    监听 chapters/ 目录变化，增量更新图
    """
    changed_files = detect_changes()
    for file in changed_files:
        remove_old_facts(file)
        ingest_chapter(file)
```

---

## 5. 与现有系统集成

### 5.1 修改 `tools.py`

```python
from novel_agent.nervus_cli import cypher_query

def smart_context_search(...):
    """使用 NervusDB Cypher 查询"""
    query = build_cypher_query(...)
    results = cypher_query(
        db_path="data/novel-graph.nervusdb",
        query=query,
        params={...}
    )
    return format_results(results)
```

### 5.2 修改 `agent.py`

```python
AGENT_CONFIGS = {
    "default": {
        "tools": [
            ...
            "smart_context_search",
            "build_character_network",
            "trace_foreshadow"
        ]
    }
}
```

### 5.3 CLI 命令

```bash
# 构建图数据库
novel-agent build-graph chapters/

# 查询上下文
novel-agent context "张三和李四的关系"

# 可视化关系网络
novel-agent visualize --character alice --output network.html
```

---

## 6. 优势对比

### 向量检索方案（弟弟）

```python
# 用户：找出张三相关章节
embeddings = embed("张三")
similar_chapters = vector_db.search(embeddings, top_k=10)

# 问题：
# 1. 只能找"提到张三"的章节
# 2. 无法找"李四提到张三"的章节
# 3. 无法找"王五和张三的朋友李四"的章节
# 4. 无法区分"张三杀了人"和"人杀了张三"
```

### 图检索方案（王道）

```cypher
// 直接提到张三
MATCH (c:Chapter)-[:contains_character]->(char:Character {name: '张三'})
RETURN c

// 李四提到张三
MATCH (c:Chapter)-[:contains_character]->(char1:Character {name: '李四'})
      -[:mentions]->(char2:Character {name: '张三'})
RETURN c

// 多跳关系
MATCH (c:Chapter)-[:contains_character]->(other:Character)
      -[:knows*1..2]->(target:Character {name: '张三'})
RETURN c, other.name AS via

// 精确因果
MATCH (c:Chapter)-[:contains]->(e:Event)-[:causes]->(result:Event)
WHERE e.actor = '张三' AND result.type = 'death'
RETURN c, result.victim
```

---

## 7. 实施计划

### Phase 1: 基础图构建 (1-2 天)
- [ ] 设计数据模型（节点/边类型）
- [ ] 实现章节解析器（提取角色、地点、事件）
- [ ] 实现 `ingest_chapter()` 函数
- [ ] 测试：导入现有章节，验证图结构

### Phase 2: 核心查询工具 (2-3 天)
- [ ] 实现 `smart_context_search()`
- [ ] 实现 `build_character_network()`
- [ ] 实现 `trace_foreshadow()`
- [ ] 添加测试用例

### Phase 3: Agent 集成 (1 天)
- [ ] 更新 `agent.py` 工具列表
- [ ] 更新 system_prompt
- [ ] 测试 Agent 调用

### Phase 4: CLI 和可视化 (2 天)
- [ ] 添加 CLI 命令
- [ ] 实现关系网络可视化（HTML）
- [ ] 添加用户文档

---

## 8. 预期效果

### 查询示例

**用户**："检查第 10 章和第 15 章的一致性"

**Agent（图检索）**：
```
🔍 正在分析第 10 章和第 15 章的关系...

📊 发现以下关联：
1. 角色关系变化：
   - 第 10 章：张三 -[hates]-> 李四 (强度 0.8)
   - 第 15 章：张三 -[loves]-> 李四 (强度 0.9)
   ⚠️  矛盾：情感态度 180° 转变，缺少过渡

2. 地点一致性：
   - 第 10 章：张三在"北京"
   - 第 15 章：张三在"上海"
   ✅ 第 12 章有"张三坐飞机去上海"的描述

3. 伏笔关联：
   - 第 10 章埋下伏笔 "foreshadow_003" (张三的秘密)
   - 第 15 章尚未揭晓
   💡 建议：在第 15 章或后续章节揭示

📈 总体一致性评分：7/10
```

**用户（向量检索，弟弟方案）**：
```
找到第 10 章和第 15 章的相似段落：
- 第 10 章第 5 段和第 15 章第 3 段相似度 0.82
（无法发现关系矛盾、无法追溯伏笔、无法理解因果）
```

---

## 9. 总结

**关键优势**：

1. **结构化知识** > 向量语义：图天然表达关系
2. **精确查询** > 近似检索：Cypher 保证完整性
3. **时间感知** > 静态快照：TemporalStore 原生支持时间线
4. **可解释性** > 黑盒推荐：清晰的路径和推理过程
5. **零成本** > API 费用：本地嵌入式，无需调用外部服务

**结论**：

> 向量检索适合"找相似文档"，图数据库适合"理解复杂关系"。
>
> 小说是关系的艺术，当然要用图数据库！🎯
