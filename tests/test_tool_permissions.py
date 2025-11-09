"""工具权限控制测试"""

from unittest.mock import MagicMock, patch

from novel_agent.agent import create_novel_agent, create_specialized_agent


class TestToolPermissions:
    """测试工具权限控制功能"""

    @patch("novel_agent.agent.create_react_agent")
    def test_allowed_tools_whitelist(self, mock_create: MagicMock) -> None:
        """测试白名单模式（--allowed-tools）

        验收标准：
        - 只加载白名单中的工具
        - 其他工具被过滤
        """
        mock_create.return_value = MagicMock()

        # 只允许读取和搜索工具
        agent = create_novel_agent(
            api_key="test-key", allowed_tools=["read_file", "search_content"]
        )

        # 验证 agent 被创建
        assert agent is not None
        mock_create.assert_called_once()

        # 验证工具数量
        call_kwargs = mock_create.call_args.kwargs
        tools = call_kwargs["tools"]
        assert len(tools) == 2

        # 验证工具名称
        tool_names = [t.name for t in tools]
        assert "read_file_tool" in tool_names
        assert "search_content_tool" in tool_names
        assert "write_chapter_tool" not in tool_names

    @patch("novel_agent.agent.create_react_agent")
    def test_disallowed_tools_blacklist(self, mock_create: MagicMock) -> None:
        """测试黑名单模式（--disallowed-tools）

        验收标准：
        - 黑名单中的工具被过滤
        - 其他工具正常加载
        """
        mock_create.return_value = MagicMock()

        # 禁止写入工具
        agent = create_novel_agent(
            api_key="test-key",
            disallowed_tools=["write_chapter", "edit_chapter_lines", "multi_edit"],
        )

        # 验证 agent 被创建
        assert agent is not None
        mock_create.assert_called_once()

        # 验证工具列表
        call_kwargs = mock_create.call_args.kwargs
        tools = call_kwargs["tools"]
        tool_names = [t.name for t in tools]

        # 验证读取工具存在
        assert "read_file_tool" in tool_names
        assert "search_content_tool" in tool_names

        # 验证写入工具被过滤
        assert "write_chapter_tool" not in tool_names
        assert "edit_chapter_lines_tool" not in tool_names
        assert "multi_edit_tool" not in tool_names

    @patch("novel_agent.agent.create_react_agent")
    def test_tools_mode_minimal(self, mock_create: MagicMock) -> None:
        """测试最小工具集模式（--tools minimal）

        验收标准：
        - 只加载只读工具
        - 写入工具被过滤
        """
        mock_create.return_value = MagicMock()

        # 使用最小工具集
        agent = create_novel_agent(api_key="test-key", tools_mode="minimal")

        # 验证 agent 被创建
        assert agent is not None
        mock_create.assert_called_once()

        # 验证工具数量
        call_kwargs = mock_create.call_args.kwargs
        tools = call_kwargs["tools"]
        assert len(tools) == 4

        # 验证工具名称
        tool_names = [t.name for t in tools]
        assert "read_file_tool" in tool_names
        assert "search_content_tool" in tool_names
        assert "verify_timeline_tool" in tool_names
        assert "verify_references_tool" in tool_names

        # 验证写入工具不存在
        assert "write_chapter_tool" not in tool_names
        assert "edit_chapter_lines_tool" not in tool_names

    @patch("novel_agent.agent.create_react_agent")
    def test_tools_mode_default_uses_agent_config(self, mock_create: MagicMock) -> None:
        """测试默认模式使用 Agent 配置的工具

        验收标准：
        - 未指定任何工具参数时，使用 Agent 配置的工具
        - outline-architect 只有 2 个工具
        """
        mock_create.return_value = MagicMock()

        # 使用 outline-architect（只有2个工具）
        agent = create_specialized_agent("outline-architect", api_key="test-key")

        # 验证 agent 被创建
        assert agent is not None
        mock_create.assert_called_once()

        # 验证工具数量（outline-architect只有2个工具）
        call_kwargs = mock_create.call_args.kwargs
        tools = call_kwargs["tools"]
        assert len(tools) == 2

        # 验证工具名称
        tool_names = [t.name for t in tools]
        assert "read_file_tool" in tool_names
        assert "search_content_tool" in tool_names

    @patch("novel_agent.agent.create_react_agent")
    def test_combined_whitelist_and_blacklist(self, mock_create: MagicMock) -> None:
        """测试白名单和黑名单组合使用

        验收标准：
        - 先应用白名单，再应用黑名单
        - 交集结果正确
        """
        mock_create.return_value = MagicMock()

        # 白名单：读取、写入、搜索
        # 黑名单：写入
        # 结果：只有读取和搜索
        agent = create_novel_agent(
            api_key="test-key",
            allowed_tools=["read_file", "write_chapter", "search_content"],
            disallowed_tools=["write_chapter"],
        )

        # 验证 agent 被创建
        assert agent is not None
        mock_create.assert_called_once()

        # 验证工具列表
        call_kwargs = mock_create.call_args.kwargs
        tools = call_kwargs["tools"]
        assert len(tools) == 2

        tool_names = [t.name for t in tools]
        assert "read_file_tool" in tool_names
        assert "search_content_tool" in tool_names
        assert "write_chapter_tool" not in tool_names

    @patch("novel_agent.agent.create_react_agent")
    def test_tools_mode_with_whitelist(self, mock_create: MagicMock) -> None:
        """测试工具模式和白名单组合

        验收标准：
        - minimal 模式 + 白名单 = 交集
        """
        mock_create.return_value = MagicMock()

        # minimal 模式（4个工具）+ 白名单（只要 read_file）
        agent = create_novel_agent(
            api_key="test-key", tools_mode="minimal", allowed_tools=["read_file"]
        )

        # 验证 agent 被创建
        assert agent is not None
        mock_create.assert_called_once()

        # 验证只有1个工具
        call_kwargs = mock_create.call_args.kwargs
        tools = call_kwargs["tools"]
        assert len(tools) == 1

        tool_names = [t.name for t in tools]
        assert "read_file_tool" in tool_names

    @patch("novel_agent.agent.create_react_agent")
    def test_empty_tools_list(self, mock_create: MagicMock) -> None:
        """测试空工具列表（过度限制）

        验收标准：
        - 即使白名单过度限制，Agent 仍能创建
        - 工具列表为空
        """
        mock_create.return_value = MagicMock()

        # 白名单中没有任何有效工具
        agent = create_novel_agent(api_key="test-key", allowed_tools=["nonexistent_tool"])

        # 验证 agent 被创建
        assert agent is not None
        mock_create.assert_called_once()

        # 验证工具列表为空
        call_kwargs = mock_create.call_args.kwargs
        tools = call_kwargs["tools"]
        assert len(tools) == 0
