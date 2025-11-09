"""上下文自动注入集成测试"""

from pathlib import Path
from unittest import mock

from langchain_core.messages import HumanMessage

from novel_agent.agent import create_specialized_agent


class TestContextIntegration:
    """测试上下文自动注入到 Agent"""

    @mock.patch("novel_agent.agent.ContextRetriever")
    @mock.patch("novel_agent.agent.ChatGoogleGenerativeAI")
    def test_context_injection_enabled(
        self, mock_llm: mock.Mock, mock_retriever_class: mock.Mock, tmp_path: Path
    ) -> None:
        """测试启用上下文注入"""
        # Mock LLM
        mock_llm_instance = mock.Mock()
        mock_llm_instance.bind.return_value = mock_llm_instance
        mock_llm.return_value = mock_llm_instance

        # Mock ContextRetriever
        mock_retriever_instance = mock.Mock()
        mock_retriever_instance.retrieve_context.return_value = [
            mock.Mock(
                path="chapters/ch001.md",
                content="第一章内容",
                source="graph",
                confidence=0.9,
            )
        ]
        mock_retriever_instance.format_context.return_value = "## 相关文档\n内容..."
        mock_retriever_class.return_value = mock_retriever_instance

        # 创建 Agent（启用上下文）
        _agent = create_specialized_agent(
            agent_type="default",
            model=mock_llm_instance,
            enable_context_retrieval=True,
            project_root=str(tmp_path),
        )

        # 验证 ContextRetriever 被初始化
        assert mock_retriever_class.called
        mock_retriever_class.assert_called_once_with(project_root=str(tmp_path))
        assert _agent is not None  # 确认返回的agent有效

    @mock.patch("novel_agent.agent.ChatGoogleGenerativeAI")
    def test_context_injection_disabled(self, mock_llm: mock.Mock, tmp_path: Path) -> None:
        """测试禁用上下文注入"""
        mock_llm_instance = mock.Mock()
        mock_llm_instance.bind.return_value = mock_llm_instance
        mock_llm.return_value = mock_llm_instance

        # 创建 Agent（禁用上下文）
        agent = create_specialized_agent(
            agent_type="default",
            model=mock_llm_instance,
            enable_context_retrieval=False,
            project_root=None,
        )

        # ContextRetriever 不应该被导入
        # (难以直接测试，通过功能测试覆盖)
        assert agent is not None

    @mock.patch("novel_agent.agent.create_react_agent")
    @mock.patch("novel_agent.agent.ContextRetriever")
    @mock.patch("novel_agent.agent.ChatGoogleGenerativeAI")
    def test_invoke_with_context_injection(
        self,
        mock_llm: mock.Mock,
        mock_retriever_class: mock.Mock,
        mock_create_agent: mock.Mock,
        tmp_path: Path,
    ) -> None:
        """测试 invoke 时自动注入上下文"""
        # Mock LLM
        mock_llm_instance = mock.Mock()
        mock_llm_instance.bind.return_value = mock_llm_instance
        mock_llm.return_value = mock_llm_instance

        # Mock ContextRetriever
        from novel_agent.context_retriever import Document

        mock_retriever_instance = mock.Mock()
        mock_retriever_instance.retrieve_context.return_value = [
            Document(
                path="chapters/ch001.md",
                content="第一章内容",
                source="graph",
                confidence=0.9,
            )
        ]
        mock_retriever_instance.format_context.return_value = "## 自动加载的相关文档\n第一章内容"
        mock_retriever_class.return_value = mock_retriever_instance

        # Mock react agent
        mock_agent_instance = mock.Mock()
        mock_agent_instance.invoke.return_value = {"messages": [mock.Mock(content="回复内容")]}
        mock_create_agent.return_value = mock_agent_instance

        # 创建 Agent
        agent = create_specialized_agent(
            agent_type="default",
            model=mock_llm_instance,
            enable_context_retrieval=True,
            project_root=str(tmp_path),
        )

        # 调用 Agent
        result = agent.invoke(
            {"messages": [HumanMessage(content="检查第1章")]}, config={"configurable": {}}
        )

        # 验证上下文检索被调用
        assert mock_retriever_instance.retrieve_context.called
        mock_retriever_instance.retrieve_context.assert_called_once_with(
            query="检查第1章", max_tokens=8000, max_docs=3
        )

        # 验证上下文格式化被调用
        assert mock_retriever_instance.format_context.called

        # 验证返回结果包含置信度
        assert "confidence" in result

    @mock.patch("novel_agent.agent.create_react_agent")
    @mock.patch("novel_agent.agent.ContextRetriever")
    @mock.patch("novel_agent.agent.ChatGoogleGenerativeAI")
    def test_invoke_without_context_when_retrieval_disabled(
        self,
        mock_llm: mock.Mock,
        mock_retriever_class: mock.Mock,
        mock_create_agent: mock.Mock,
        tmp_path: Path,
    ) -> None:
        """测试禁用上下文检索时不注入"""
        # Mock LLM
        mock_llm_instance = mock.Mock()
        mock_llm_instance.bind.return_value = mock_llm_instance
        mock_llm.return_value = mock_llm_instance

        # Mock react agent
        mock_agent_instance = mock.Mock()
        mock_agent_instance.invoke.return_value = {"messages": [mock.Mock(content="回复内容")]}
        mock_create_agent.return_value = mock_agent_instance

        # 创建 Agent（禁用上下文）
        agent = create_specialized_agent(
            agent_type="default",
            model=mock_llm_instance,
            enable_context_retrieval=False,
            project_root=None,
        )

        # 调用 Agent
        result = agent.invoke(
            {"messages": [HumanMessage(content="检查第1章")]}, config={"configurable": {}}
        )

        # 验证 ContextRetriever 没有被初始化
        assert not mock_retriever_class.called

        # 验证返回结果包含置信度
        assert "confidence" in result
