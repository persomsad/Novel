"""测试终端输入位置优化"""

from unittest.mock import patch

from novel_agent.cli import _get_optimal_input_offset


def test_get_optimal_input_offset_normal_terminal() -> None:
    """测试正常终端高度"""
    with patch("shutil.get_terminal_size") as mock_size:
        # 模拟 40 行终端（MacBook 默认）
        mock_size.return_value.lines = 40

        offset = _get_optimal_input_offset()

        # 40 * 0.65 = 26，offset = 40 - 26 = 14
        # 但限制在 3-10 之间，所以是 10
        assert offset == 10


def test_get_optimal_input_offset_large_terminal() -> None:
    """测试大屏终端"""
    with patch("shutil.get_terminal_size") as mock_size:
        # 模拟 60 行终端
        mock_size.return_value.lines = 60

        offset = _get_optimal_input_offset()

        # 60 * 0.65 = 39，offset = 60 - 39 = 21
        # 限制在最大 10
        assert offset == 10


def test_get_optimal_input_offset_small_terminal() -> None:
    """测试小终端"""
    with patch("shutil.get_terminal_size") as mock_size:
        # 模拟 20 行终端
        mock_size.return_value.lines = 20

        offset = _get_optimal_input_offset()

        # 20 * 0.65 = 13，offset = 20 - 13 = 7
        assert offset == 7


def test_get_optimal_input_offset_very_small_terminal() -> None:
    """测试极小终端"""
    with patch("shutil.get_terminal_size") as mock_size:
        # 模拟 10 行终端
        mock_size.return_value.lines = 10

        offset = _get_optimal_input_offset()

        # 10 * 0.65 = 6.5 → 6，offset = 10 - 6 = 4
        # 限制在最小 3
        assert offset == 4


def test_get_optimal_input_offset_minimum() -> None:
    """测试最小偏移"""
    with patch("shutil.get_terminal_size") as mock_size:
        # 模拟超小终端
        mock_size.return_value.lines = 8

        offset = _get_optimal_input_offset()

        # 8 * 0.65 = 5.2 → 5，offset = 8 - 5 = 3
        # 限制在最小 3
        assert offset == 3


def test_get_optimal_input_offset_error_handling() -> None:
    """测试错误处理"""
    with patch("shutil.get_terminal_size") as mock_size:
        # 模拟无法获取终端大小
        mock_size.side_effect = AttributeError()

        offset = _get_optimal_input_offset()

        # 应该返回默认值 5
        assert offset == 5


def test_get_optimal_input_offset_value_error() -> None:
    """测试 ValueError 处理"""
    with patch("shutil.get_terminal_size") as mock_size:
        # 模拟 ValueError
        mock_size.side_effect = ValueError()

        offset = _get_optimal_input_offset()

        # 应该返回默认值 5
        assert offset == 5


def test_offset_range_always_valid() -> None:
    """测试偏移量始终在有效范围"""
    test_heights = [8, 10, 15, 20, 25, 30, 40, 50, 60, 100]

    with patch("shutil.get_terminal_size") as mock_size:
        for height in test_heights:
            mock_size.return_value.lines = height
            offset = _get_optimal_input_offset()

            # 偏移量必须在 3-10 之间
            assert 3 <= offset <= 10, f"Height {height} → offset {offset} out of range"
