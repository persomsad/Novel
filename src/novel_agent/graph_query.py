"""图查询模块 - 智能上下文检索

此模块提供：
1. smart_context_search - 智能搜索相关上下文
2. build_character_network - 构建角色关系网络
3. trace_foreshadow - 追溯伏笔链条
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .nervus_cli import NervusCLIConfig, cypher_query


@dataclass
class SearchResult:
    """搜索结果"""

    type: str  # 'chapter' | 'character' | 'event' | 'foreshadow'
    name: str
    relevance: str  # 关联类型
    path: list[str]  # 图路径
    properties: dict[str, Any]
    confidence: float


@dataclass
class NetworkNode:
    """网络节点"""

    id: str
    label: str
    type: str
    properties: dict[str, Any]


@dataclass
class NetworkEdge:
    """网络边"""

    source: str
    target: str
    relation: str
    weight: float
    properties: dict[str, Any]


class GraphQuerier:
    """图查询器"""

    def __init__(self, db_path: str, config: NervusCLIConfig | None = None) -> None:
        self.db_path = db_path
        self.config = config or NervusCLIConfig()

    def smart_context_search(
        self,
        query: str,
        search_type: Literal["character", "location", "event", "foreshadow", "all"] = "all",
        max_hops: int = 2,
        time_range: tuple[str, str] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """智能搜索相关上下文

        Args:
            query: 用户查询（如"张三和李四的关系"）
            search_type: 搜索类型
            max_hops: 最大关系跳数
            time_range: 时间范围 (start, end)
            limit: 最多返回条数

        Returns:
            {
                "results": [...],
                "summary": "...",
                "graph_stats": {...}
            }
        """
        # 简单实现：搜索包含关键词的节点
        results: list[SearchResult] = []

        # 查询 1：直接匹配
        direct_query = """
        MATCH (n)
        WHERE n.name CONTAINS $keyword OR n.description CONTAINS $keyword
        RETURN n.name AS name, labels(n)[0] AS type, properties(n) AS props
        LIMIT $limit
        """

        direct_results = cypher_query(
            db_path=self.db_path,
            query=direct_query,
            params={"keyword": query, "limit": limit},
            config=self.config,
        )

        for row in direct_results.get("rows", []):
            results.append(
                SearchResult(
                    type=row.get("type", "unknown"),
                    name=row.get("name", ""),
                    relevance="direct_match",
                    path=[row.get("name", "")],
                    properties=row.get("props", {}),
                    confidence=1.0,
                )
            )

        # 查询 2：关系关联（多跳）
        if max_hops > 0:
            relation_query = f"""
            MATCH path = (start)-[*1..{max_hops}]-(end)
            WHERE start.name CONTAINS $keyword
            RETURN end.name AS name,
                   labels(end)[0] AS type,
                   properties(end) AS props,
                   length(path) AS hops,
                   [n IN nodes(path) | n.name] AS path_nodes
            LIMIT $limit
            """

            relation_results = cypher_query(
                db_path=self.db_path,
                query=relation_query,
                params={"keyword": query, "limit": limit},
                config=self.config,
            )

            for row in relation_results.get("rows", []):
                hops = row.get("hops", 1)
                results.append(
                    SearchResult(
                        type=row.get("type", "unknown"),
                        name=row.get("name", ""),
                        relevance=f"related_{hops}_hops",
                        path=row.get("path_nodes", []),
                        properties=row.get("props", {}),
                        confidence=1.0 / (hops + 1),  # 跳数越多，置信度越低
                    )
                )

        # 排序（置信度降序）
        results.sort(key=lambda r: r.confidence, reverse=True)
        results = results[:limit]

        # 构建摘要
        summary = self._build_summary(results, query)

        # 统计信息
        stats = {
            "nodes_searched": len(results),
            "max_depth": max(len(r.path) for r in results) if results else 0,
            "types_found": list({r.type for r in results}),
        }

        return {
            "results": [
                {
                    "type": r.type,
                    "name": r.name,
                    "relevance": r.relevance,
                    "path": r.path,
                    "properties": r.properties,
                    "confidence": r.confidence,
                }
                for r in results
            ],
            "summary": summary,
            "graph_stats": stats,
        }

    def build_character_network(
        self, character_names: list[str] | None = None, min_strength: float = 0.0
    ) -> dict[str, Any]:
        """构建角色关系网络

        Args:
            character_names: 角色名列表（None=所有角色）
            min_strength: 最小关系强度

        Returns:
            {
                "nodes": [...],
                "edges": [...],
                "clusters": [...]
            }
        """
        # 查询角色节点
        if character_names:
            char_filter = "WHERE n.name IN $names"
            params: dict[str, Any] = {"names": character_names}
        else:
            char_filter = ""
            params = {}

        nodes_query = f"""
        MATCH (n:character)
        {char_filter}
        RETURN n.name AS name, properties(n) AS props
        """

        nodes_result = cypher_query(
            db_path=self.db_path, query=nodes_query, params=params, config=self.config
        )

        nodes = [
            NetworkNode(
                id=row.get("name", ""),
                label=row.get("name", ""),
                type="character",
                properties=row.get("props", {}),
            )
            for row in nodes_result.get("rows", [])
        ]

        # 查询角色关系
        edges_query = """
        MATCH (a:character)-[r]->(b:character)
        RETURN a.name AS source,
               b.name AS target,
               type(r) AS relation,
               properties(r) AS props
        """

        edges_result = cypher_query(db_path=self.db_path, query=edges_query, config=self.config)

        edges = [
            NetworkEdge(
                source=row.get("source", ""),
                target=row.get("target", ""),
                relation=row.get("relation", ""),
                weight=row.get("props", {}).get("strength", 1.0),
                properties=row.get("props", {}),
            )
            for row in edges_result.get("rows", [])
            if row.get("props", {}).get("strength", 1.0) >= min_strength
        ]

        # 简单社区检测（基于连通分量）
        clusters = self._detect_communities(nodes, edges)

        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.type,
                    "properties": n.properties,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "weight": e.weight,
                    "properties": e.properties,
                }
                for e in edges
            ],
            "clusters": clusters,
        }

    def trace_foreshadow(self, foreshadow_id: str) -> dict[str, Any]:
        """追溯伏笔完整链条

        Args:
            foreshadow_id: 伏笔 ID

        Returns:
            {
                "foreshadow_id": "...",
                "setup": {...},
                "hints": [...],
                "reveal": {...},
                "status": "resolved" | "unresolved"
            }
        """
        # 查询伏笔节点
        foreshadow_query = """
        MATCH (f:foreshadow {id: $foreshadow_id})
        RETURN properties(f) AS props
        """

        foreshadow_result = cypher_query(
            db_path=self.db_path,
            query=foreshadow_query,
            params={"foreshadow_id": foreshadow_id},
            config=self.config,
        )

        if not foreshadow_result.get("rows"):
            return {
                "error": f"伏笔 {foreshadow_id} 不存在",
                "foreshadow_id": foreshadow_id,
            }

        foreshadow_props = foreshadow_result["rows"][0].get("props", {})

        # 查询 setup 章节
        setup_query = """
        MATCH (c:chapter)-[:mentions_foreshadow]->(f:foreshadow {id: $foreshadow_id})
        RETURN c.number AS chapter, properties(c) AS props
        ORDER BY c.number ASC
        LIMIT 1
        """

        setup_result = cypher_query(
            db_path=self.db_path,
            query=setup_query,
            params={"foreshadow_id": foreshadow_id},
            config=self.config,
        )

        setup = (
            {
                "chapter": setup_result["rows"][0].get("chapter"),
                "properties": setup_result["rows"][0].get("props", {}),
            }
            if setup_result.get("rows")
            else None
        )

        # 查询所有提及（hints）
        hints_query = """
        MATCH (c:chapter)-[:mentions_foreshadow]->(f:foreshadow {id: $foreshadow_id})
        RETURN c.number AS chapter, properties(c) AS props
        ORDER BY c.number ASC
        """

        hints_result = cypher_query(
            db_path=self.db_path,
            query=hints_query,
            params={"foreshadow_id": foreshadow_id},
            config=self.config,
        )

        hints = [
            {"chapter": row.get("chapter"), "properties": row.get("props", {})}
            for row in hints_result.get("rows", [])
        ]

        # 查询 reveal（如果有 fulfills 关系）
        reveal_query = """
        MATCH (f:foreshadow {id: $foreshadow_id})-[:fulfills]->(c:chapter)
        RETURN c.number AS chapter, properties(c) AS props
        """

        reveal_result = cypher_query(
            db_path=self.db_path,
            query=reveal_query,
            params={"foreshadow_id": foreshadow_id},
            config=self.config,
        )

        reveal = (
            {
                "chapter": reveal_result["rows"][0].get("chapter"),
                "properties": reveal_result["rows"][0].get("props", {}),
            }
            if reveal_result.get("rows")
            else None
        )

        status = "resolved" if reveal else "unresolved"

        return {
            "foreshadow_id": foreshadow_id,
            "properties": foreshadow_props,
            "setup": setup,
            "hints": hints,
            "reveal": reveal,
            "status": status,
        }

    def _build_summary(self, results: list[SearchResult], query: str) -> str:
        """构建搜索结果摘要"""
        if not results:
            return f"未找到与 '{query}' 相关的内容"

        type_counts: dict[str, int] = {}
        for r in results:
            type_counts[r.type] = type_counts.get(r.type, 0) + 1

        summary_parts = [f"找到 {len(results)} 个相关结果："]
        for typ, count in type_counts.items():
            summary_parts.append(f"  - {typ}: {count} 个")

        return "\n".join(summary_parts)

    def _detect_communities(
        self, nodes: list[NetworkNode], edges: list[NetworkEdge]
    ) -> list[dict[str, Any]]:
        """简单社区检测（连通分量）"""
        # 构建邻接表
        graph: dict[str, set[str]] = {node.id: set() for node in nodes}
        for edge in edges:
            graph[edge.source].add(edge.target)
            graph[edge.target].add(edge.source)  # 无向图

        # DFS 查找连通分量
        visited: set[str] = set()
        communities: list[dict[str, Any]] = []

        def dfs(node_id: str, component: list[str]) -> None:
            visited.add(node_id)
            component.append(node_id)
            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    dfs(neighbor, component)

        cluster_id = 1
        for node in nodes:
            if node.id not in visited:
                component: list[str] = []
                dfs(node.id, component)
                if component:
                    communities.append(
                        {
                            "id": cluster_id,
                            "members": component,
                            "size": len(component),
                            "label": f"社区 {cluster_id}",
                        }
                    )
                    cluster_id += 1

        return communities


def smart_context_search(
    query: str,
    db_path: str = "data/novel-graph.nervusdb",
    search_type: Literal["character", "location", "event", "foreshadow", "all"] = "all",
    max_hops: int = 2,
    limit: int = 10,
) -> dict[str, Any]:
    """智能上下文搜索（便捷函数）"""
    querier = GraphQuerier(db_path)
    return querier.smart_context_search(
        query=query, search_type=search_type, max_hops=max_hops, limit=limit
    )


def build_character_network(
    db_path: str = "data/novel-graph.nervusdb",
    character_names: list[str] | None = None,
) -> dict[str, Any]:
    """构建角色关系网络（便捷函数）"""
    querier = GraphQuerier(db_path)
    return querier.build_character_network(character_names)


def trace_foreshadow(
    foreshadow_id: str, db_path: str = "data/novel-graph.nervusdb"
) -> dict[str, Any]:
    """追溯伏笔（便捷函数）"""
    querier = GraphQuerier(db_path)
    return querier.trace_foreshadow(foreshadow_id)


__all__ = [
    "SearchResult",
    "NetworkNode",
    "NetworkEdge",
    "GraphQuerier",
    "smart_context_search",
    "build_character_network",
    "trace_foreshadow",
]
