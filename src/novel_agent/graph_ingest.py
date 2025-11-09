"""图数据库摄取模块 - 将小说内容构建为知识图谱

此模块负责：
1. 解析章节内容，提取实体（角色、地点、事件）
2. 识别实体间的关系
3. 构建时间线
4. 将数据写入 NervusDB
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .nervus_cli import NervusCLIConfig, cypher_query


@dataclass
class Entity:
    """实体（角色、地点、事件等）"""

    name: str
    type: str  # 'character' | 'location' | 'event' | 'chapter'
    properties: dict[str, Any]


@dataclass
class Relation:
    """实体关系"""

    source: str
    predicate: str
    target: str
    properties: dict[str, Any]


class ChapterParser:
    """章节解析器 - 提取实体和关系"""

    def __init__(self) -> None:
        # 时间标记模式
        self.time_pattern = re.compile(
            r"`(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)?)`"
        )
        # 引用标记模式
        self.ref_pattern = re.compile(r"`@ref\[([^\]]+)\]`")
        # 角色提及模式（简单版本，实际可用 NER）
        self.character_pattern = re.compile(
            r"([A-Za-z\u4e00-\u9fa5]{2,4})(?:说|道|想|做|去|来|看|听)"
        )

    def parse_chapter(self, chapter_path: str) -> tuple[list[Entity], list[Relation]]:
        """解析单个章节，返回实体和关系"""
        with open(chapter_path, encoding="utf-8") as f:
            content = f.read()

        chapter_num = self._extract_chapter_number(chapter_path)
        entities: list[Entity] = []
        relations: list[Relation] = []

        # 创建章节实体
        chapter_entity = Entity(
            name=f"ch{chapter_num:03d}",
            type="chapter",
            properties={
                "number": chapter_num,
                "path": chapter_path,
                "word_count": len(content),
                "title": self._extract_title(content),
            },
        )
        entities.append(chapter_entity)

        # 提取时间标记
        time_marks = self.time_pattern.findall(content)
        if time_marks:
            for i, time_str in enumerate(time_marks):
                event_entity = Entity(
                    name=f"event_ch{chapter_num:03d}_{i}",
                    type="event",
                    properties={
                        "timestamp": time_str,
                        "chapter": chapter_num,
                        "description": f"时间点 {time_str}",
                    },
                )
                entities.append(event_entity)

                # 章节包含事件
                relations.append(
                    Relation(
                        source=chapter_entity.name,
                        predicate="contains_event",
                        target=event_entity.name,
                        properties={"chapter": chapter_num},
                    )
                )

        # 提取引用标记（伏笔）
        refs = self.ref_pattern.findall(content)
        for ref_id in refs:
            foreshadow_entity = Entity(
                name=f"foreshadow_{ref_id}",
                type="foreshadow",
                properties={
                    "id": ref_id,
                    "chapter": chapter_num,
                    "status": "mentioned",
                },
            )
            entities.append(foreshadow_entity)

            relations.append(
                Relation(
                    source=chapter_entity.name,
                    predicate="mentions_foreshadow",
                    target=foreshadow_entity.name,
                    properties={"chapter": chapter_num},
                )
            )

        # 提取角色提及（简单模式匹配）
        characters = self._extract_characters(content)
        for char_name in characters:
            char_entity = Entity(name=char_name, type="character", properties={"name": char_name})
            entities.append(char_entity)

            relations.append(
                Relation(
                    source=chapter_entity.name,
                    predicate="contains_character",
                    target=char_name,
                    properties={"chapter": chapter_num},
                )
            )

        return entities, relations

    def _extract_chapter_number(self, path: str) -> int:
        """从文件路径提取章节号"""
        match = re.search(r"ch(\d+)", path)
        if match:
            return int(match.group(1))
        return 0

    def _extract_title(self, content: str) -> str:
        """提取章节标题（第一行）"""
        lines = content.strip().split("\n")
        if lines:
            title = lines[0].strip("#").strip()
            return title[:100]  # 限制长度
        return ""

    def _extract_characters(self, content: str) -> set[str]:
        """提取角色名（简单模式匹配）"""
        matches = self.character_pattern.findall(content)
        # 过滤常见词
        stopwords = {"他", "她", "我", "你", "我们", "他们", "那", "这"}
        return {name for name in matches if name not in stopwords and len(name) >= 2}


class GraphBuilder:
    """图数据库构建器"""

    def __init__(self, db_path: str, config: NervusCLIConfig | None = None) -> None:
        self.db_path = db_path
        self.config = config or NervusCLIConfig()
        self.parser = ChapterParser()

    def ingest_chapter(self, chapter_path: str) -> dict[str, Any]:
        """摄取单个章节到图数据库"""
        entities, relations = self.parser.parse_chapter(chapter_path)

        stats = {"entities_created": 0, "relations_created": 0, "errors": []}

        # 创建实体（节点）
        for entity in entities:
            try:
                self._create_node(entity)
                stats["entities_created"] += 1
            except Exception as e:
                stats["errors"].append(f"创建节点失败 {entity.name}: {e}")

        # 创建关系（边）
        for relation in relations:
            try:
                self._create_edge(relation)
                stats["relations_created"] += 1
            except Exception as e:
                stats["errors"].append(f"创建关系失败 {relation.source}->{relation.target}: {e}")

        return stats

    def ingest_directory(self, chapters_dir: str) -> dict[str, Any]:
        """批量摄取目录下所有章节"""
        chapters = sorted(Path(chapters_dir).glob("ch*.md"))
        total_stats = {
            "chapters_processed": 0,
            "entities_created": 0,
            "relations_created": 0,
            "errors": [],
        }

        for chapter_path in chapters:
            print(f"正在处理: {chapter_path.name}")
            stats = self.ingest_chapter(str(chapter_path))

            total_stats["chapters_processed"] += 1
            total_stats["entities_created"] += stats["entities_created"]
            total_stats["relations_created"] += stats["relations_created"]
            total_stats["errors"].extend(stats["errors"])

        return total_stats

    def _create_node(self, entity: Entity) -> None:
        """创建节点（使用 Cypher）"""
        # 构建属性字符串
        props_str = ", ".join(
            f"{k}: ${k}" for k in entity.properties if entity.properties[k] is not None
        )

        query = f"""
        MERGE (n:{entity.type} {{name: $name}})
        SET n += {{{props_str}}}
        RETURN n
        """

        params = {"name": entity.name, **entity.properties}

        cypher_query(
            db_path=self.db_path,
            query=query,
            params=params,
            readonly=False,
            config=self.config,
        )

    def _create_edge(self, relation: Relation) -> None:
        """创建关系（边）"""
        props_str = ", ".join(
            f"{k}: ${k}" for k in relation.properties if relation.properties[k] is not None
        )

        query = f"""
        MATCH (a {{name: $source}}), (b {{name: $target}})
        MERGE (a)-[r:{relation.predicate}]->(b)
        SET r += {{{props_str}}}
        RETURN r
        """

        params = {
            "source": relation.source,
            "target": relation.target,
            **relation.properties,
        }

        cypher_query(
            db_path=self.db_path,
            query=query,
            params=params,
            readonly=False,
            config=self.config,
        )

    def clear_graph(self) -> None:
        """清空图数据库（危险操作！）"""
        query = "MATCH (n) DETACH DELETE n"
        cypher_query(db_path=self.db_path, query=query, readonly=False, config=self.config)


def build_graph_from_chapters(chapters_dir: str, db_path: str) -> dict[str, Any]:
    """一键构建图数据库（主入口）"""
    builder = GraphBuilder(db_path)

    # 清空旧数据（可选）
    # builder.clear_graph()

    # 批量摄取
    stats = builder.ingest_directory(chapters_dir)

    print("\n" + "=" * 50)
    print("📊 图构建完成！")
    print(f"处理章节: {stats['chapters_processed']}")
    print(f"创建实体: {stats['entities_created']}")
    print(f"创建关系: {stats['relations_created']}")
    if stats["errors"]:
        print(f"⚠️  错误数: {len(stats['errors'])}")
        for err in stats["errors"][:5]:  # 只显示前 5 个
            print(f"  - {err}")
    print("=" * 50)

    return stats


__all__ = [
    "Entity",
    "Relation",
    "ChapterParser",
    "GraphBuilder",
    "build_graph_from_chapters",
]
