"""测试置信度评分功能"""

from unittest.mock import MagicMock

from novel_agent.agent import _estimate_confidence


class TestConfidenceScoring:
    """测试置信度评分算法"""

    def test_empty_messages_returns_zero(self) -> None:
        """测试空消息返回0"""
        assert _estimate_confidence([]) == 0
        assert _estimate_confidence(None) == 0

    def test_short_response_low_score(self) -> None:
        """测试过短回答得分低"""
        message = MagicMock()
        message.content = "好的"
        score = _estimate_confidence([message])
        assert score < 40  # 太短，分数低

    def test_appropriate_length_base_score(self) -> None:
        """测试适当长度获得基础分"""
        message = MagicMock()
        message.content = (
            "我已经检查了章节内容，发现了一些问题。"
            "首先，时间线有些不连贯。其次，角色描写需要更加细致。"
            "建议修改相关部分以提升质量。"
        )
        score = _estimate_confidence([message])
        assert 40 <= score <= 80  # 适中长度，有基础分

    def test_structured_response_bonus(self) -> None:
        """测试结构化回答加分"""
        message = MagicMock()
        message.content = """我已经仔细分析了章节内容，发现了以下几个需要注意的问题和改进建议：

## 主要问题
- 时间线在某些地方不够连贯，需要调整
- 角色描写不够细致，缺少性格特征和情感描写

## 建议
1. 修改时间标记，确保前后连贯
2. 补充角色细节，增加心理描写
3. 检查对话是否符合人物性格
"""
        score = _estimate_confidence([message])
        assert score >= 50  # 结构化好，有加分

    def test_file_reference_quality_bonus(self) -> None:
        """测试包含文件引用加分"""
        message = MagicMock()
        message.content = """检查 chapters/ch001.md 第42行发现了一个时间标记问题。建议修改为：
```
[TIME:2024-01-15]
```
这样可以确保时间线的连贯性。
"""
        score = _estimate_confidence([message])
        assert score >= 65  # 有文件路径、行号、代码示例

    def test_error_markers_penalty(self) -> None:
        """测试错误标记扣分"""
        message = MagicMock()
        message.content = "检查发现3个问题：❌ 时间错误 ❌ 引用缺失 ❌ 格式问题"
        score = _estimate_confidence([message])
        assert score < 60  # 有错误标记，扣分

    def test_uncertain_response_penalty(self) -> None:
        """测试不确定回答扣分"""
        message = MagicMock()
        message.content = "我不清楚这个问题，需要更多信息才能判断。"
        score = _estimate_confidence([message])
        assert score < 40  # 空洞回答，大幅扣分

    def test_high_quality_response(self) -> None:
        """测试高质量回答得高分"""
        message = MagicMock()
        message.content = """## 一致性检查结果

检查了 chapters/ch003.md，发现以下问题：

### 时间线问题
- **第23行**：[TIME:2024-01-15] 与前章不连贯
- **建议**：修改为 [TIME:2024-01-16]

### 角色描写
- **第45行**：主角性格与 spec/knowledge/character-profiles.md 中的设定不符
- **建议**：参考设定补充描写

### 引用完整性
- ✅ 所有引用都已定义
- ✅ 时间标记格式正确

例如，可以这样修改第23行：
```markdown
[TIME:2024-01-16]  # 第二天
```
"""
        score = _estimate_confidence([message])
        assert score >= 80  # 高质量：结构化、有文件路径、有建议、有示例

    def test_score_range_0_to_100(self) -> None:
        """测试评分范围在0-100之间"""
        # 极端情况：非常长的重复文本
        message = MagicMock()
        message.content = "不清楚 " * 1000 + "❌ " * 100
        score = _estimate_confidence([message])
        assert 0 <= score <= 100

    def test_practical_example_medium_quality(self) -> None:
        """测试实际使用场景：中等质量回答"""
        message = MagicMock()
        message.content = """我检查了第3章，发现角色张三的描写有些问题：

- 性格变化突然
- 与前面章节不一致

建议参考 spec/knowledge/character-profiles.md 调整。
"""
        score = _estimate_confidence([message])
        assert 45 <= score <= 65  # 中等质量：有结构、有建议、有文件引用
