"""智能上下文检索器

基于 NervusDB 图数据库 + ripgrep 文本搜索的混合检索策略，
自动选择与用户查询最相关的文档。

灵感来源：Claude Code 使用 ripgrep 而非向量检索
优势：精确、快速、零成本、可解释
"""

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .graph_query import GraphQuerier
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Document:
    """文档对象"""

    path: str  # 文件路径
    content: str  # 文档内容
    source: str  # 来源：graph / grep / index
    confidence: float  # 置信度 (0-1)
    context: Optional[str] = None  # 上下文片段
    metadata: Optional[dict[str, Any]] = None  # 元数据

    def __hash__(self) -> int:
        return hash(self.path)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Document):
            return False
        return self.path == other.path


class ContextRetriever:
    """智能上下文检索器

    策略（按优先级）：
    1. 图查询：从 NervusDB 找出直接关联的实体
    2. 文本搜索：用 ripgrep 找包含关键词的文档
    3. 时间线过滤：只返回相关时间段的章节
    4. 优先级排序：章节 > 设定 > 大纲
    """

    def __init__(
        self,
        project_root: str | Path,
        graph_db_path: Optional[str] = None,
        index_path: Optional[str] = None,
    ):
        """初始化检索器

        Args:
            project_root: 项目根目录
            graph_db_path: 图数据库路径（可选）
            index_path: 连续性索引路径（可选）
        """
        self.project_root = Path(project_root)

        # 图查询器
        if graph_db_path is None:
            graph_db_path = str(self.project_root / "data" / "novel-graph.nervusdb")

        self.graph_db_path = graph_db_path
        self.graph_querier: Optional[GraphQuerier] = None

        # 连续性索引
        if index_path is None:
            index_path = str(self.project_root / "data" / "continuity" / "index.json")

        self.index_path = index_path
        self.index: Optional[dict[str, Any]] = None

        # 加载索引
        self._load_index()

        # 检查图数据库
        if Path(graph_db_path).exists():
            try:
                self.graph_querier = GraphQuerier(graph_db_path)
                logger.info("✓ 图数据库已加载")
            except Exception as e:
                logger.warning(f"图数据库加载失败: {e}")
        else:
            logger.warning(f"图数据库不存在: {graph_db_path}")

    def _load_index(self) -> None:
        """加载连续性索引"""
        if not Path(self.index_path).exists():
            logger.warning(f"索引文件不存在: {self.index_path}")
            self.index = {"characters": [], "locations": [], "chapters": []}
            return

        try:
            with open(self.index_path, encoding="utf-8") as f:
                self.index = json.load(f)
            logger.info(f"✓ 索引已加载: {len(self.index.get('characters', []))} 角色")
        except Exception as e:
            logger.error(f"索引加载失败: {e}")
            self.index = {"characters": [], "locations": [], "chapters": []}

    def retrieve_context(
        self, query: str, max_tokens: int = 10000, max_docs: int = 5
    ) -> list[Document]:
        """智能检索相关上下文

        Args:
            query: 用户查询
            max_tokens: 最大 token 数（粗略估计：1 token ≈ 1.5 字符）
            max_docs: 最多返回文档数

        Returns:
            按相关性排序的文档列表
        """
        logger.info(f"开始检索上下文，查询: {query}")

        # 1. 提取实体
        entities = self._extract_entities(query)
        logger.debug(f"提取实体: {entities}")

        # 2. 图查询
        docs_by_graph = self._query_by_graph(entities)
        logger.debug(f"图查询结果: {len(docs_by_graph)} 个文档")

        # 3. grep 搜索
        docs_by_grep = self._grep_search(query)
        logger.debug(f"grep 搜索结果: {len(docs_by_grep)} 个文档")

        # 4. 合并去重
        all_docs = self._merge_documents(docs_by_graph, docs_by_grep)
        logger.debug(f"合并后: {len(all_docs)} 个文档")

        # 5. 优先级排序
        ranked_docs = self._rank_documents(all_docs, query)

        # 6. 限制数量和 token
        limited_docs = self._limit_documents(ranked_docs, max_docs, max_tokens)

        logger.info(f"✓ 检索完成，返回 {len(limited_docs)} 个文档")
        return limited_docs

    def _extract_entities(self, query: str) -> list[tuple[str, str]]:
        """从查询中提取实体（角色、地点等）

        Args:
            query: 用户查询

        Returns:
            实体列表 [(类型, 名称), ...]
        """
        if self.index is None:
            return []

        entities = []

        # 提取角色
        for char in self.index.get("characters", []):
            name = char.get("name", "")
            if name and name in query:
                entities.append(("character", name))

        # 提取地点
        for loc in self.index.get("locations", []):
            name = loc.get("name", "")
            if name and name in query:
                entities.append(("location", name))

        # 提取章节号
        chapter_pattern = r"第?\s*(\d+)\s*章"
        matches = re.findall(chapter_pattern, query)
        for match in matches:
            entities.append(("chapter", f"ch{int(match):03d}"))

        return entities

    def _query_by_graph(self, entities: list[tuple[str, str]]) -> list[Document]:
        """通过图查询相关文档

        Args:
            entities: 实体列表

        Returns:
            文档列表
        """
        if not self.graph_querier or not entities:
            return []

        docs = []

        for entity_type, entity_name in entities:
            try:
                # 从图中搜索实体
                # 将 entity_type 转换为 Literal 类型
                search_type: Any = entity_type
                result = self.graph_querier.smart_context_search(
                    query=entity_name, search_type=search_type, max_hops=1, limit=10
                )

                # 提取文档路径
                for item in result.get("results", []):
                    # 从元数据中提取章节信息
                    if "metadata" in item:
                        chapter_num = item["metadata"].get("chapter")
                        if chapter_num:
                            doc_path = f"chapters/ch{chapter_num:03d}.md"
                            docs.append(
                                Document(
                                    path=doc_path,
                                    content="",  # 稍后加载
                                    source="graph",
                                    confidence=item.get("confidence", 0.9),
                                    metadata={"entity": entity_name, "type": entity_type},
                                )
                            )

            except Exception as e:
                logger.warning(f"图查询失败 ({entity_name}): {e}")

        return docs

    def _grep_search(self, query: str) -> list[Document]:
        """使用 ripgrep 搜索文本

        Args:
            query: 搜索关键词

        Returns:
            文档列表
        """
        docs = []

        try:
            # 构建搜索路径
            search_paths = [
                str(self.project_root / "chapters"),
                str(self.project_root / "spec"),
            ]

            # 过滤存在的路径
            search_paths = [p for p in search_paths if Path(p).exists()]

            if not search_paths:
                logger.warning("没有可搜索的路径")
                return []

            # 使用 rg 搜索（JSON 格式输出）
            result = subprocess.run(
                [
                    "rg",
                    "--json",
                    "--max-count=3",  # 每个文件最多3个匹配
                    "--ignore-case",  # 忽略大小写
                    query,
                ]
                + search_paths,
                capture_output=True,
                text=True,
                timeout=5,
            )

            # 解析 JSON 输出
            seen_files = set()
            for line in result.stdout.splitlines():
                try:
                    match = json.loads(line)
                    if match.get("type") == "match":
                        data = match.get("data", {})
                        path_data = data.get("path", {})
                        file_path = path_data.get("text", "")

                        # 去重
                        if file_path in seen_files:
                            continue
                        seen_files.add(file_path)

                        # 提取匹配的行文本作为上下文
                        lines_data = data.get("lines", {})
                        context = lines_data.get("text", "").strip()

                        # 转换为相对路径
                        try:
                            rel_path = str(Path(file_path).relative_to(self.project_root))
                        except ValueError:
                            rel_path = file_path

                        docs.append(
                            Document(
                                path=rel_path,
                                content="",  # 稍后加载
                                source="grep",
                                confidence=0.8,
                                context=context,
                            )
                        )

                except json.JSONDecodeError:
                    continue

        except FileNotFoundError:
            logger.warning("ripgrep 未安装，跳过文本搜索")
        except subprocess.TimeoutExpired:
            logger.warning("ripgrep 搜索超时")
        except Exception as e:
            logger.warning(f"grep 搜索失败: {e}")

        return docs

    def _merge_documents(
        self, docs_by_graph: list[Document], docs_by_grep: list[Document]
    ) -> list[Document]:
        """合并并去重文档

        Args:
            docs_by_graph: 图查询结果
            docs_by_grep: grep 搜索结果

        Returns:
            合并后的文档列表
        """
        # 使用 dict 去重（保留更高置信度的）
        docs_map: dict[str, Document] = {}

        for doc in docs_by_graph + docs_by_grep:
            if doc.path not in docs_map:
                docs_map[doc.path] = doc
            else:
                # 保留置信度更高的
                if doc.confidence > docs_map[doc.path].confidence:
                    docs_map[doc.path] = doc

        return list(docs_map.values())

    def _rank_documents(self, docs: list[Document], query: str) -> list[Document]:
        """优先级排序

        Args:
            docs: 文档列表
            query: 查询关键词

        Returns:
            排序后的文档列表
        """

        def priority_score(doc: Document) -> float:
            score = doc.confidence

            # 文件类型优先级
            if "chapters/" in doc.path:
                score += 1.0  # 章节优先
            elif "spec/knowledge/" in doc.path:
                score += 0.8  # 设定次之
            elif "spec/outline.md" in doc.path:
                score += 0.5  # 大纲最后

            # 来源优先级
            if doc.source == "graph":
                score += 0.2  # 图查询更精确

            # 文件名匹配
            if query.lower() in doc.path.lower():
                score += 0.3

            return score

        return sorted(docs, key=priority_score, reverse=True)

    def _limit_documents(
        self, docs: list[Document], max_docs: int, max_tokens: int
    ) -> list[Document]:
        """限制文档数量和 token 数

        Args:
            docs: 排序后的文档列表
            max_docs: 最大文档数
            max_tokens: 最大 token 数

        Returns:
            限制后的文档列表
        """
        limited_docs = []
        total_tokens: float = 0.0

        for doc in docs[:max_docs]:
            # 加载文档内容
            if not doc.content:
                doc.content = self._load_document_content(doc.path)

            # 估算 token 数（粗略：1 token ≈ 1.5 字符）
            doc_tokens = len(doc.content) / 1.5

            if total_tokens + doc_tokens > max_tokens:
                # 截断文档
                remaining_tokens = max_tokens - total_tokens
                remaining_chars = int(remaining_tokens * 1.5)
                doc.content = doc.content[:remaining_chars] + "\n\n... (已截断)"
                limited_docs.append(doc)
                break

            limited_docs.append(doc)
            total_tokens += doc_tokens

        return limited_docs

    def _load_document_content(self, path: str) -> str:
        """加载文档内容

        Args:
            path: 文件相对路径

        Returns:
            文档内容
        """
        full_path = self.project_root / path

        if not full_path.exists():
            logger.warning(f"文档不存在: {path}")
            return ""

        try:
            with open(full_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"加载文档失败 ({path}): {e}")
            return ""

    def format_context(self, docs: list[Document]) -> str:
        """格式化上下文为文本

        Args:
            docs: 文档列表

        Returns:
            格式化的上下文文本
        """
        if not docs:
            return ""

        lines = ["## 自动加载的相关文档\n"]

        for i, doc in enumerate(docs, 1):
            lines.append(f"### 文档 {i}: {doc.path}")
            lines.append(f"来源: {doc.source} (置信度: {doc.confidence:.2f})")
            lines.append("")
            lines.append("```")
            lines.append(doc.content)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)
