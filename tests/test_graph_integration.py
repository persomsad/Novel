"""图数据库集成测试"""

from pathlib import Path
from unittest import mock

from novel_agent.graph_ingest import ChapterParser, Entity, GraphBuilder, Relation
from novel_agent.graph_query import GraphQuerier


class TestChapterParser:
    """测试章节解析器"""

    def test_parse_chapter_extracts_entities(self, tmp_path: Path) -> None:
        """测试提取实体"""
        chapter = tmp_path / "ch001.md"
        chapter.write_text(
            "# 第一章\n\n"
            '张三说："你好！"\n'
            '李四道："再见！"\n'
            "`2024-01-15` 这是一个时间标记\n"
            "`@ref[foreshadow_001]` 这是一个伏笔\n",
            encoding="utf-8",
        )

        parser = ChapterParser()
        entities, relations = parser.parse_chapter(str(chapter))

        # 验证章节实体
        chapter_entities = [e for e in entities if e.type == "chapter"]
        assert len(chapter_entities) == 1
        assert chapter_entities[0].name == "ch001"

        # 验证角色实体
        character_entities = [e for e in entities if e.type == "character"]
        character_names = {e.name for e in character_entities}
        assert "张三" in character_names
        assert "李四" in character_names

        # 验证事件实体（时间标记）
        event_entities = [e for e in entities if e.type == "event"]
        assert len(event_entities) >= 1

        # 验证伏笔实体
        foreshadow_entities = [e for e in entities if e.type == "foreshadow"]
        assert len(foreshadow_entities) >= 1
        assert any("foreshadow_001" in e.name for e in foreshadow_entities)

    def test_parse_chapter_extracts_relations(self, tmp_path: Path) -> None:
        """测试提取关系"""
        chapter = tmp_path / "ch002.md"
        chapter.write_text(
            "# 第二章\n\n" '张三说："你好！"\n' "`2024-01-16` 这是一个时间标记\n",
            encoding="utf-8",
        )

        parser = ChapterParser()
        entities, relations = parser.parse_chapter(str(chapter))

        # 验证章节包含角色关系
        char_relations = [r for r in relations if r.predicate == "contains_character"]
        assert len(char_relations) >= 1

        # 验证章节包含事件关系
        event_relations = [r for r in relations if r.predicate == "contains_event"]
        assert len(event_relations) >= 1

    def test_extract_chapter_number(self) -> None:
        """测试提取章节号"""
        parser = ChapterParser()
        assert parser._extract_chapter_number("chapters/ch001.md") == 1
        assert parser._extract_chapter_number("chapters/ch042.md") == 42
        assert parser._extract_chapter_number("test/ch999.md") == 999

    def test_extract_title(self) -> None:
        """测试提取标题"""
        parser = ChapterParser()
        assert parser._extract_title("# 第一章：开始\n\n内容...") == "第一章：开始"
        assert parser._extract_title("## 第二章\n\n内容...") == "第二章"
        # 无标题时返回第一行内容（截断到 100 字符）
        assert parser._extract_title("内容...") == "内容..."


class TestGraphBuilder:
    """测试图构建器"""

    @mock.patch("novel_agent.graph_ingest.cypher_query")
    def test_create_node(self, mock_cypher: mock.Mock) -> None:
        """测试创建节点"""
        mock_cypher.return_value = {"rows": []}

        builder = GraphBuilder("test.nervusdb")
        entity = Entity(name="alice", type="character", properties={"age": 25, "gender": "female"})

        builder._create_node(entity)

        # 验证调用了 Cypher
        assert mock_cypher.called
        call_args = mock_cypher.call_args
        assert "MERGE" in call_args.kwargs["query"]
        assert call_args.kwargs["params"]["name"] == "alice"

    @mock.patch("novel_agent.graph_ingest.cypher_query")
    def test_create_edge(self, mock_cypher: mock.Mock) -> None:
        """测试创建关系"""
        mock_cypher.return_value = {"rows": []}

        builder = GraphBuilder("test.nervusdb")
        relation = Relation(
            source="alice",
            predicate="knows",
            target="bob",
            properties={"since": 2021},
        )

        builder._create_edge(relation)

        # 验证调用了 Cypher
        assert mock_cypher.called
        call_args = mock_cypher.call_args
        assert "MATCH" in call_args.kwargs["query"]
        assert "MERGE" in call_args.kwargs["query"]
        assert call_args.kwargs["params"]["source"] == "alice"
        assert call_args.kwargs["params"]["target"] == "bob"

    @mock.patch("novel_agent.graph_ingest.cypher_query")
    def test_ingest_chapter(self, mock_cypher: mock.Mock, tmp_path: Path) -> None:
        """测试摄取单个章节"""
        mock_cypher.return_value = {"rows": []}

        chapter = tmp_path / "ch001.md"
        chapter.write_text("# 第一章\n\n张三说话了\n`2024-01-15` 时间点\n", encoding="utf-8")

        builder = GraphBuilder("test.nervusdb")
        stats = builder.ingest_chapter(str(chapter))

        # 验证统计信息
        assert stats["entities_created"] > 0
        assert stats["relations_created"] > 0
        assert isinstance(stats["errors"], list)


class TestGraphQuerier:
    """测试图查询器"""

    @mock.patch("novel_agent.graph_query.cypher_query")
    def test_smart_context_search_direct_match(self, mock_cypher: mock.Mock) -> None:
        """测试直接匹配搜索"""
        mock_cypher.return_value = {
            "rows": [
                {
                    "name": "张三",
                    "type": "character",
                    "props": {"age": 25, "gender": "male"},
                }
            ]
        }

        querier = GraphQuerier("test.nervusdb")
        result = querier.smart_context_search(query="张三", max_hops=0)

        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "张三"
        assert result["results"][0]["type"] == "character"
        assert result["results"][0]["confidence"] == 1.0

    @mock.patch("novel_agent.graph_query.cypher_query")
    def test_build_character_network(self, mock_cypher: mock.Mock) -> None:
        """测试构建角色网络"""
        mock_cypher.side_effect = [
            # 第一次调用：查询节点
            {
                "rows": [
                    {"name": "alice", "props": {"type": "protagonist"}},
                    {"name": "bob", "props": {"type": "supporting"}},
                ]
            },
            # 第二次调用：查询边
            {
                "rows": [
                    {
                        "source": "alice",
                        "target": "bob",
                        "relation": "knows",
                        "props": {"strength": 0.9},
                    }
                ]
            },
        ]

        querier = GraphQuerier("test.nervusdb")
        result = querier.build_character_network()

        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1
        assert result["edges"][0]["source"] == "alice"
        assert result["edges"][0]["target"] == "bob"

    @mock.patch("novel_agent.graph_query.cypher_query")
    def test_trace_foreshadow_resolved(self, mock_cypher: mock.Mock) -> None:
        """测试追溯已解决的伏笔"""
        mock_cypher.side_effect = [
            # 伏笔属性查询
            {"rows": [{"props": {"id": "foreshadow_001", "description": "测试伏笔"}}]},
            # setup 查询
            {"rows": [{"chapter": 5, "props": {"title": "第五章"}}]},
            # hints 查询
            {
                "rows": [
                    {"chapter": 5, "props": {"title": "第五章"}},
                    {"chapter": 8, "props": {"title": "第八章"}},
                ]
            },
            # reveal 查询
            {"rows": [{"chapter": 20, "props": {"title": "第二十章"}}]},
        ]

        querier = GraphQuerier("test.nervusdb")
        result = querier.trace_foreshadow("foreshadow_001")

        assert result["foreshadow_id"] == "foreshadow_001"
        assert result["status"] == "resolved"
        assert result["setup"]["chapter"] == 5
        assert len(result["hints"]) == 2
        assert result["reveal"]["chapter"] == 20

    @mock.patch("novel_agent.graph_query.cypher_query")
    def test_trace_foreshadow_unresolved(self, mock_cypher: mock.Mock) -> None:
        """测试追溯未解决的伏笔"""
        mock_cypher.side_effect = [
            {"rows": [{"props": {"id": "foreshadow_002"}}]},
            {"rows": [{"chapter": 10, "props": {}}]},
            {"rows": [{"chapter": 10, "props": {}}]},
            {"rows": []},  # 无 reveal
        ]

        querier = GraphQuerier("test.nervusdb")
        result = querier.trace_foreshadow("foreshadow_002")

        assert result["status"] == "unresolved"
        assert result["reveal"] is None

    @mock.patch("novel_agent.graph_query.cypher_query")
    def test_trace_nonexistent_foreshadow(self, mock_cypher: mock.Mock) -> None:
        """测试追溯不存在的伏笔"""
        mock_cypher.return_value = {"rows": []}

        querier = GraphQuerier("test.nervusdb")
        result = querier.trace_foreshadow("foreshadow_999")

        assert "error" in result
        assert "不存在" in result["error"]


class TestGraphIntegration:
    """集成测试"""

    @mock.patch("novel_agent.graph_ingest.cypher_query")
    def test_full_ingest_workflow(self, mock_cypher: mock.Mock, tmp_path: Path) -> None:
        """测试完整摄取流程"""
        mock_cypher.return_value = {"rows": []}

        # 创建测试章节
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        (chapters_dir / "ch001.md").write_text(
            "# 第一章\n\n张三说话\n`2024-01-15` 时间\n", encoding="utf-8"
        )
        (chapters_dir / "ch002.md").write_text(
            "# 第二章\n\n李四出现\n`2024-01-16` 时间\n", encoding="utf-8"
        )

        # 构建图
        builder = GraphBuilder("test.nervusdb")
        stats = builder.ingest_directory(str(chapters_dir))

        # 验证统计
        assert stats["chapters_processed"] == 2
        assert stats["entities_created"] > 0
        assert stats["relations_created"] > 0
