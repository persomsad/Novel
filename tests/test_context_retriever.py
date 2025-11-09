"""上下文检索器测试"""

import json
from pathlib import Path
from unittest import mock

from novel_agent.context_retriever import ContextRetriever, Document


class TestDocument:
    """测试 Document 数据类"""

    def test_init(self) -> None:
        """测试初始化"""
        doc = Document(
            path="chapters/ch001.md",
            content="内容",
            source="graph",
            confidence=0.9,
        )

        assert doc.path == "chapters/ch001.md"
        assert doc.content == "内容"
        assert doc.source == "graph"
        assert doc.confidence == 0.9

    def test_equality(self) -> None:
        """测试相等性（基于路径）"""
        doc1 = Document(path="chapters/ch001.md", content="内容1", source="graph", confidence=0.9)
        doc2 = Document(path="chapters/ch001.md", content="内容2", source="grep", confidence=0.8)
        doc3 = Document(path="chapters/ch002.md", content="内容3", source="graph", confidence=0.9)

        assert doc1 == doc2  # 同一路径
        assert doc1 != doc3  # 不同路径

    def test_hashable(self) -> None:
        """测试可哈希（可以放入集合）"""
        doc1 = Document(path="chapters/ch001.md", content="内容", source="graph", confidence=0.9)
        doc2 = Document(path="chapters/ch002.md", content="内容", source="graph", confidence=0.9)

        docs_set = {doc1, doc2}
        assert len(docs_set) == 2


class TestContextRetriever:
    """测试上下文检索器"""

    def test_init(self, tmp_path: Path) -> None:
        """测试初始化"""
        retriever = ContextRetriever(project_root=tmp_path)

        assert retriever.project_root == tmp_path
        assert retriever.index is not None

    def test_load_index(self, tmp_path: Path) -> None:
        """测试加载索引"""
        # 创建索引文件
        index_path = tmp_path / "data" / "continuity" / "index.json"
        index_path.parent.mkdir(parents=True)

        index_data = {
            "characters": [{"name": "张三"}, {"name": "李四"}],
            "locations": [{"name": "北京"}],
            "chapters": [],
        }

        index_path.write_text(json.dumps(index_data, ensure_ascii=False))

        # 加载
        retriever = ContextRetriever(project_root=tmp_path)

        assert retriever.index is not None
        assert len(retriever.index["characters"]) == 2
        assert len(retriever.index["locations"]) == 1

    def test_extract_entities_characters(self, tmp_path: Path) -> None:
        """测试提取角色实体"""
        # 创建索引
        index_path = tmp_path / "data" / "continuity" / "index.json"
        index_path.parent.mkdir(parents=True)

        index_data = {
            "characters": [{"name": "张三"}, {"name": "李四"}],
            "locations": [],
        }

        index_path.write_text(json.dumps(index_data, ensure_ascii=False))

        retriever = ContextRetriever(project_root=tmp_path)

        # 提取实体
        entities = retriever._extract_entities("张三和李四的关系")

        assert ("character", "张三") in entities
        assert ("character", "李四") in entities

    def test_extract_entities_chapters(self, tmp_path: Path) -> None:
        """测试提取章节号"""
        retriever = ContextRetriever(project_root=tmp_path)

        # 测试不同格式
        entities = retriever._extract_entities("检查第3章")
        assert ("chapter", "ch003") in entities

        entities = retriever._extract_entities("第 5 章的内容")
        assert ("chapter", "ch005") in entities

        entities = retriever._extract_entities("3章有问题")
        assert ("chapter", "ch003") in entities

    def test_merge_documents_dedup(self, tmp_path: Path) -> None:
        """测试文档合并去重"""
        retriever = ContextRetriever(project_root=tmp_path)

        docs_by_graph = [
            Document(path="chapters/ch001.md", content="", source="graph", confidence=0.9),
            Document(path="chapters/ch002.md", content="", source="graph", confidence=0.8),
        ]

        docs_by_grep = [
            Document(path="chapters/ch001.md", content="", source="grep", confidence=0.7),  # 重复
            Document(path="chapters/ch003.md", content="", source="grep", confidence=0.8),
        ]

        merged = retriever._merge_documents(docs_by_graph, docs_by_grep)

        # 应该去重，ch001 保留 graph 的（置信度更高）
        assert len(merged) == 3
        paths = [doc.path for doc in merged]
        assert "chapters/ch001.md" in paths
        assert "chapters/ch002.md" in paths
        assert "chapters/ch003.md" in paths

        # 验证保留了更高置信度的
        ch001_doc = next(d for d in merged if d.path == "chapters/ch001.md")
        assert ch001_doc.confidence == 0.9

    def test_rank_documents_priority(self, tmp_path: Path) -> None:
        """测试文档优先级排序"""
        retriever = ContextRetriever(project_root=tmp_path)

        docs = [
            Document(path="spec/outline.md", content="", source="grep", confidence=0.8),
            Document(path="chapters/ch001.md", content="", source="graph", confidence=0.8),
            Document(
                path="spec/knowledge/characters.md",
                content="",
                source="grep",
                confidence=0.8,
            ),
        ]

        ranked = retriever._rank_documents(docs, "test")

        # 章节 > 设定 > 大纲
        assert ranked[0].path == "chapters/ch001.md"
        assert ranked[1].path == "spec/knowledge/characters.md"
        assert ranked[2].path == "spec/outline.md"

    def test_load_document_content(self, tmp_path: Path) -> None:
        """测试加载文档内容"""
        # 创建测试文档
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        test_file = chapters_dir / "ch001.md"
        test_content = "# 第一章\n\n测试内容"
        test_file.write_text(test_content, encoding="utf-8")

        retriever = ContextRetriever(project_root=tmp_path)

        # 加载内容
        content = retriever._load_document_content("chapters/ch001.md")

        assert content == test_content

    def test_limit_documents_count(self, tmp_path: Path) -> None:
        """测试限制文档数量"""
        # 创建测试文档
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        for i in range(10):
            (chapters_dir / f"ch{i+1:03d}.md").write_text(f"章节 {i+1}")

        retriever = ContextRetriever(project_root=tmp_path)

        docs = [
            Document(path=f"chapters/ch{i+1:03d}.md", content="", source="graph", confidence=0.9)
            for i in range(10)
        ]

        # 限制为 3 个文档
        limited = retriever._limit_documents(docs, max_docs=3, max_tokens=100000)

        assert len(limited) <= 3

    def test_limit_documents_tokens(self, tmp_path: Path) -> None:
        """测试限制 token 数"""
        # 创建测试文档
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()

        (chapters_dir / "ch001.md").write_text("短内容")
        (chapters_dir / "ch002.md").write_text("长" * 1000)

        retriever = ContextRetriever(project_root=tmp_path)

        docs = [
            Document(path="chapters/ch001.md", content="", source="graph", confidence=0.9),
            Document(path="chapters/ch002.md", content="", source="graph", confidence=0.8),
        ]

        # 限制 token 数
        limited = retriever._limit_documents(docs, max_docs=10, max_tokens=100)

        # 验证 token 限制生效
        total_content = "".join([doc.content for doc in limited])
        assert len(total_content) <= 100 * 1.5 + 100  # 考虑截断提示

    def test_format_context(self, tmp_path: Path) -> None:
        """测试格式化上下文"""
        retriever = ContextRetriever(project_root=tmp_path)

        docs = [
            Document(
                path="chapters/ch001.md",
                content="第一章内容",
                source="graph",
                confidence=0.9,
            ),
            Document(
                path="spec/knowledge/characters.md",
                content="角色设定",
                source="grep",
                confidence=0.8,
            ),
        ]

        context_text = retriever.format_context(docs)

        # 验证格式
        assert "## 自动加载的相关文档" in context_text
        assert "文档 1: chapters/ch001.md" in context_text
        assert "文档 2: spec/knowledge/characters.md" in context_text
        assert "第一章内容" in context_text
        assert "角色设定" in context_text

    @mock.patch("novel_agent.context_retriever.GraphQuerier")
    @mock.patch("novel_agent.context_retriever.subprocess.run")
    def test_retrieve_context_integration(
        self, mock_subprocess: mock.Mock, mock_graph: mock.Mock, tmp_path: Path
    ) -> None:
        """集成测试：完整检索流程"""
        # Mock 图查询
        mock_graph_instance = mock.Mock()
        mock_graph_instance.smart_context_search.return_value = {
            "results": [
                {
                    "name": "张三",
                    "confidence": 0.9,
                    "metadata": {"chapter": 1},
                }
            ]
        }
        mock_graph.return_value = mock_graph_instance

        # Mock grep
        mock_result = mock.Mock()
        mock_result.stdout = json.dumps(
            {
                "type": "match",
                "data": {
                    "path": {"text": str(tmp_path / "chapters" / "ch002.md")},
                    "lines": {"text": "李四出现了"},
                },
            }
        )
        mock_subprocess.return_value = mock_result

        # 创建测试文档
        chapters_dir = tmp_path / "chapters"
        chapters_dir.mkdir()
        (chapters_dir / "ch001.md").write_text("第一章")
        (chapters_dir / "ch002.md").write_text("第二章")

        # 创建索引
        index_path = tmp_path / "data" / "continuity" / "index.json"
        index_path.parent.mkdir(parents=True)
        index_data = {"characters": [{"name": "张三"}], "locations": []}
        index_path.write_text(json.dumps(index_data, ensure_ascii=False))

        # 检索
        retriever = ContextRetriever(project_root=tmp_path, graph_db_path=str(tmp_path / "test.db"))

        docs = retriever.retrieve_context("张三", max_docs=5)

        # 验证结果
        assert len(docs) >= 1
        assert any("ch001.md" in doc.path or "ch002.md" in doc.path for doc in docs)
