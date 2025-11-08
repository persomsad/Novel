"""Tests for novel_agent.agent"""

from unittest.mock import Mock, patch

import pytest

from novel_agent.agent import create_novel_agent, create_specialized_agent


class TestCreateNovelAgent:
    """测试 create_novel_agent 函数"""

    def test_create_agent_with_api_key(self) -> None:
        """测试使用 API key 创建 Agent"""
        with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_gemini:
            with patch("novel_agent.agent.create_react_agent") as mock_create:
                mock_model = Mock()
                mock_gemini.return_value = mock_model
                mock_create.return_value = Mock()

                agent = create_novel_agent(api_key="test-api-key")

                # 验证 Gemini 被正确初始化
                mock_gemini.assert_called_once()
                call_kwargs = mock_gemini.call_args.kwargs
                assert call_kwargs["model"] == "gemini-2.0-flash-exp"
                assert call_kwargs["google_api_key"] == "test-api-key"
                assert call_kwargs["temperature"] == 0.7

                # 验证 ReAct Agent 被创建
                mock_create.assert_called_once()
                assert agent is not None

    def test_create_agent_with_custom_model(self) -> None:
        """测试使用自定义模型创建 Agent"""
        with patch("novel_agent.agent.create_react_agent") as mock_create:
            mock_model = Mock()
            mock_model.bind.return_value = mock_model  # Mock bind() method
            mock_create.return_value = Mock()

            agent = create_novel_agent(model=mock_model)

            # 验证使用了自定义模型（已被bind包装）
            mock_create.assert_called_once()
            # 模型会被bind包装，所以检查bind是否被调用
            mock_model.bind.assert_called_once()
            assert agent is not None

    def test_create_agent_no_api_key_raises(self) -> None:
        """测试缺少 API key 时抛出异常"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="未找到 Gemini API Key"):
                create_novel_agent()

    def test_create_agent_with_env_api_key(self) -> None:
        """测试从环境变量读取 API key"""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env-api-key"}):
            with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_gemini:
                with patch("novel_agent.agent.create_react_agent") as mock_create:
                    mock_model = Mock()
                    mock_gemini.return_value = mock_model
                    mock_create.return_value = Mock()

                    _ = create_novel_agent()

                    # 验证使用了环境变量中的 API key
                    call_kwargs = mock_gemini.call_args.kwargs
                    assert call_kwargs["google_api_key"] == "env-api-key"


class TestCreateSpecializedAgent:
    """测试 create_specialized_agent 函数"""

    def test_create_default_agent(self) -> None:
        """测试创建默认Agent"""
        with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_gemini:
            with patch("novel_agent.agent.create_react_agent") as mock_create:
                mock_model = Mock()
                mock_gemini.return_value = mock_model
                mock_create.return_value = Mock()

                agent = create_specialized_agent("default", api_key="test-key")

                # 验证Agent被创建
                mock_create.assert_called_once()
                assert agent is not None

    def test_create_unknown_agent_type_raises(self) -> None:
        """测试创建未知类型Agent时抛出异常"""
        with pytest.raises(ValueError, match="未知的Agent类型"):
            create_specialized_agent("unknown-type", api_key="test-key")

    def test_backward_compatibility(self) -> None:
        """测试向后兼容：create_novel_agent调用create_specialized_agent"""
        with patch("novel_agent.agent.create_specialized_agent") as mock_specialized:
            mock_specialized.return_value = Mock()

            agent = create_novel_agent(api_key="test-key")

            # 验证调用了create_specialized_agent with "default"
            mock_specialized.assert_called_once()
            call_args = mock_specialized.call_args
            assert call_args[0][0] == "default"  # 第一个位置参数是agent_type
            assert agent is not None
