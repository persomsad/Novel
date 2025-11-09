"""模型配置测试"""

import os
from unittest.mock import MagicMock, patch

import pytest

from novel_agent.agent import create_specialized_agent


class TestModelConfig:
    """模型配置测试"""

    def test_default_model(self):
        """测试默认模型配置"""
        with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_chat:
            mock_chat.return_value = MagicMock()

            # 不设置环境变量，使用默认值
            with patch.dict(os.environ, {}, clear=True):
                os.environ["GOOGLE_API_KEY"] = "test-key"
                create_specialized_agent(api_key="test-key")

                # 验证使用默认模型
                mock_chat.assert_called_once()
                call_args = mock_chat.call_args
                assert call_args[1]["model"] == "gemini-2.0-flash-exp"
                assert call_args[1]["temperature"] == 0.7

    def test_custom_model_from_env(self):
        """测试从环境变量读取自定义模型"""
        with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_chat:
            mock_chat.return_value = MagicMock()

            # 设置自定义模型
            with patch.dict(
                os.environ,
                {
                    "GOOGLE_API_KEY": "test-key",
                    "GOOGLE_MODEL": "gemini-1.5-pro",
                    "GOOGLE_TEMPERATURE": "0.5",
                },
            ):
                create_specialized_agent(api_key="test-key")

                # 验证使用自定义模型
                mock_chat.assert_called_once()
                call_args = mock_chat.call_args
                assert call_args[1]["model"] == "gemini-1.5-pro"
                assert call_args[1]["temperature"] == 0.5

    def test_custom_model_partial_config(self):
        """测试部分自定义配置"""
        with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_chat:
            mock_chat.return_value = MagicMock()

            # 只设置模型名称，使用默认温度
            with patch.dict(
                os.environ,
                {"GOOGLE_API_KEY": "test-key", "GOOGLE_MODEL": "gemini-1.5-flash"},
                clear=True,
            ):
                create_specialized_agent(api_key="test-key")

                # 验证
                mock_chat.assert_called_once()
                call_args = mock_chat.call_args
                assert call_args[1]["model"] == "gemini-1.5-flash"
                assert call_args[1]["temperature"] == 0.7  # 默认值

    def test_temperature_parsing(self):
        """测试温度参数解析"""
        with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_chat:
            mock_chat.return_value = MagicMock()

            # 测试不同温度值
            test_cases = ["0.0", "0.3", "0.7", "1.0"]

            for temp in test_cases:
                mock_chat.reset_mock()
                with patch.dict(
                    os.environ,
                    {"GOOGLE_API_KEY": "test-key", "GOOGLE_TEMPERATURE": temp},
                    clear=True,
                ):
                    create_specialized_agent(api_key="test-key")

                    call_args = mock_chat.call_args
                    assert call_args[1]["temperature"] == float(temp)

    def test_invalid_temperature(self):
        """测试无效温度值"""
        with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_chat:
            mock_chat.return_value = MagicMock()

            # 设置无效温度
            with patch.dict(
                os.environ,
                {"GOOGLE_API_KEY": "test-key", "GOOGLE_TEMPERATURE": "invalid"},
                clear=True,
            ):
                # 应该抛出 ValueError
                with pytest.raises(ValueError):
                    create_specialized_agent(api_key="test-key")

    def test_custom_model_object(self):
        """测试传入自定义模型对象"""
        custom_model = MagicMock()

        # 传入自定义模型对象，不应该创建新的 ChatGoogleGenerativeAI
        with patch("novel_agent.agent.ChatGoogleGenerativeAI") as mock_chat:
            agent = create_specialized_agent(model=custom_model, api_key="test-key")

            # 不应该调用 ChatGoogleGenerativeAI
            mock_chat.assert_not_called()

            # agent 应该使用传入的模型
            assert agent is not None
