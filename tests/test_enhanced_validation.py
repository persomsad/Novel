"""Tests for enhanced validation functions

测试增强的验证脚本：
- verify_strict_timeline (增强版)
- verify_strict_references (增强版)
"""

import json
from pathlib import Path

import pytest

from novel_agent.tools import verify_strict_references, verify_strict_timeline


class TestVerifyStrictTimelineEnhanced:
    """测试增强版 verify_strict_timeline 函数"""

    def test_returns_structured_result(self) -> None:
        """测试返回结构化结果"""
        result = verify_strict_timeline()

        # 验证结构
        assert isinstance(result, dict)
        assert "errors" in result
        assert "warnings" in result
        assert "summary" in result

        # 验证类型
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
        assert isinstance(result["summary"], dict)

        # 验证 summary 字段
        summary = result["summary"]
        assert "total_errors" in summary
        assert "total_warnings" in summary
        assert "auto_fixable" in summary
        assert isinstance(summary["total_errors"], int)
        assert isinstance(summary["total_warnings"], int)
        assert isinstance(summary["auto_fixable"], bool)

    def test_error_contains_required_fields(self, tmp_path: Path) -> None:
        """测试错误对象包含必需字段"""
        # 创建测试索引（模拟时间线错误）
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "time_markers": [{"value": "2077-03-15", "line": 10}],
                },
                {
                    "chapter_id": "ch002",
                    "time_markers": [{"value": "2077-03-10", "line": 20}],  # 时间倒退！
                },
            ]
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_timeline(index_path)

        # 应该检测到错误
        assert result["summary"]["total_errors"] > 0

        # 验证错误对象的结构
        error = result["errors"][0]
        assert "file" in error
        assert "line" in error
        assert "type" in error
        assert "message" in error
        assert "suggestion" in error
        assert "current_value" in error

        # 验证具体内容
        assert error["file"] == "chapters/ch002.md"
        assert error["line"] == 20
        assert error["type"] == "timeline_inconsistency"
        assert "时间倒退" in error["message"]
        assert "expected_value" in error  # 应该有修复建议
        assert error["expected_value"] == "2077-03-16"

    def test_suggestion_provides_fix(self, tmp_path: Path) -> None:
        """测试修复建议提供具体的修复方案"""
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "time_markers": [{"value": "2077-01-01", "line": 5}],
                },
                {
                    "chapter_id": "ch002",
                    "time_markers": [{"value": "2076-12-31", "line": 10}],  # 早于上一章
                },
            ]
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_timeline(index_path)

        error = result["errors"][0]

        # 建议应该包含具体的修复值
        assert "suggestion" in error
        assert "[TIME:" in error["suggestion"]
        assert error["expected_value"] == "2077-01-02"  # 前一天 + 1
        assert "改为" in error["suggestion"]

    def test_auto_fixable_flag(self, tmp_path: Path) -> None:
        """测试 auto_fixable 标志"""
        # 时间线错误可以自动修复（有 expected_value）
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "time_markers": [{"value": "2077-03-15", "line": 10}],
                },
                {
                    "chapter_id": "ch002",
                    "time_markers": [{"value": "2077-03-10", "line": 20}],
                },
            ]
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_timeline(index_path)

        assert result["summary"]["auto_fixable"] is True

    def test_unparseable_time_warning(self, tmp_path: Path) -> None:
        """测试无法解析的时间标记"""
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "time_markers": [{"value": "invalid-date", "line": 15}],  # 无效格式
                }
            ]
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_timeline(index_path)

        # 应该有警告而非错误
        assert result["summary"]["total_warnings"] > 0

        warning = result["warnings"][0]
        assert warning["type"] == "unparseable_time"
        assert "无法解析" in warning["message"]
        assert "YYYY-MM-DD" in warning["suggestion"]

    def test_multiple_time_formats(self, tmp_path: Path) -> None:
        """测试支持多种时间格式"""
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "time_markers": [
                        {"value": "2077-01-01", "line": 10},  # YYYY-MM-DD
                    ],
                },
                {
                    "chapter_id": "ch002",
                    "time_markers": [
                        {"value": "2077/01/02", "line": 20},  # YYYY/MM/DD
                    ],
                },
                {
                    "chapter_id": "ch003",
                    "time_markers": [
                        {"value": "2077.01.03", "line": 30},  # YYYY.MM.DD
                    ],
                },
            ]
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_timeline(index_path)

        # 所有格式都应该能解析，无错误
        assert result["summary"]["total_errors"] == 0

    def test_summary_counts_match(self, tmp_path: Path) -> None:
        """测试 summary 计数与实际错误/警告数量匹配"""
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "time_markers": [{"value": "2077-03-15", "line": 10}],
                },
                {
                    "chapter_id": "ch002",
                    "time_markers": [{"value": "2077-03-10", "line": 20}],  # 错误
                },
                {
                    "chapter_id": "ch003",
                    "time_markers": [{"value": "invalid", "line": 30}],  # 警告
                },
            ]
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_timeline(index_path)

        assert result["summary"]["total_errors"] == len(result["errors"])
        assert result["summary"]["total_warnings"] == len(result["warnings"])


class TestVerifyStrictReferencesEnhanced:
    """测试增强版 verify_strict_references 函数"""

    def test_returns_structured_result(self) -> None:
        """测试返回结构化结果"""
        result = verify_strict_references()

        # 验证结构
        assert isinstance(result, dict)
        assert "errors" in result
        assert "warnings" in result
        assert "summary" in result

        # 验证 summary 字段
        summary = result["summary"]
        assert "total_errors" in summary
        assert "total_warnings" in summary
        assert "auto_fixable" in summary

    def test_undefined_reference_error(self, tmp_path: Path) -> None:
        """测试未定义的引用错误"""
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "references": [
                        {
                            "id": "undefined_ref",  # 未定义
                            "line": 25,
                        }
                    ],
                }
            ],
            "references": [],  # 空的引用定义列表
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_references(index_path)

        # 应该检测到错误
        assert result["summary"]["total_errors"] > 0

        error = result["errors"][0]
        assert error["type"] == "undefined_reference"
        assert error["file"] == "chapters/ch001.md"
        assert error["line"] == 25
        assert "未定义" in error["message"]
        assert "spec/knowledge/" in error["suggestion"]

    def test_unused_reference_warning(self, tmp_path: Path) -> None:
        """测试未使用的引用定义警告"""
        index_data = {
            "chapters": [],  # 没有章节使用引用
            "references": [
                {
                    "id": "unused_ref",
                    "occurrences": [],  # 无章节使用
                }
            ],
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_references(index_path)

        # 应该有警告
        assert result["summary"]["total_warnings"] > 0

        warning = result["warnings"][0]
        assert warning["type"] == "unused_reference"
        assert "无任何章节使用" in warning["message"]
        assert "[REF:" in warning["suggestion"]

    def test_references_not_auto_fixable(self, tmp_path: Path) -> None:
        """测试引用验证不能自动修复"""
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "references": [{"id": "undefined", "line": 10}],
                }
            ],
            "references": [],
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_references(index_path)

        # 引用错误通常需要手动定义，不能自动修复
        assert result["summary"]["auto_fixable"] is False

    def test_error_provides_specific_suggestion(self, tmp_path: Path) -> None:
        """测试错误提供具体的修复建议"""
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "references": [{"id": "mystery_item", "line": 42}],
                }
            ],
            "references": [],
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_references(index_path)

        error = result["errors"][0]

        # 建议应该提供两种解决方案
        suggestion = error["suggestion"]
        assert "spec/knowledge/" in suggestion or "拼写错误" in suggestion

    def test_multiple_error_types(self, tmp_path: Path) -> None:
        """测试多种错误类型"""
        index_data = {
            "chapters": [
                {
                    "chapter_id": "ch001",
                    "references": [
                        {"id": "undefined1", "line": 10},  # 未定义
                        {"id": "undefined2", "line": 20},  # 未定义
                    ],
                }
            ],
            "references": [
                {
                    "id": "unused_ref",
                    "occurrences": [],  # 未使用
                }
            ],
        }

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_references(index_path)

        # 应该有 2 个错误（undefined1, undefined2）
        assert result["summary"]["total_errors"] == 2

        # 应该有 1 个警告（unused_ref）
        assert result["summary"]["total_warnings"] == 1

    def test_empty_index_no_errors(self, tmp_path: Path) -> None:
        """测试空索引无错误"""
        index_data = {"chapters": [], "references": []}

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        result = verify_strict_references(index_path)

        assert result["summary"]["total_errors"] == 0
        assert result["summary"]["total_warnings"] == 0


class TestEnhancedValidationEdgeCases:
    """测试边缘情况"""

    def test_missing_index_file(self) -> None:
        """测试索引文件不存在时的处理"""
        # 使用不存在的路径
        non_existent = Path("/tmp/nonexistent_index_12345.json")

        # 应该抛出 FileNotFoundError
        with pytest.raises(FileNotFoundError, match="连续性索引"):
            verify_strict_timeline(non_existent)

    def test_malformed_index_handled_gracefully(self, tmp_path: Path) -> None:
        """测试畸形索引文件的处理"""
        index_path = tmp_path / "malformed.json"
        index_path.write_text("not a valid json", encoding="utf-8")

        # 应该抛出 JSONDecodeError
        import json

        with pytest.raises(json.JSONDecodeError):
            verify_strict_timeline(index_path)

    def test_line_number_zero_for_nervus_errors(self, tmp_path: Path) -> None:
        """测试 NervusDB 错误的行号为 0"""
        # NervusDB 相关错误无法定位到具体行
        # 应该使用 line: 0 表示

        index_data = {"chapters": [], "references": []}

        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps(index_data), encoding="utf-8")

        # 使用无效的 NervusDB 路径触发错误
        result = verify_strict_timeline(index_path, db_path="/invalid/path.db")

        # 如果有 NervusDB 错误，line 应该是 0
        nervus_errors = [e for e in result.get("warnings", []) if e.get("file") == "NervusDB"]
        if nervus_errors:
            assert all(e["line"] == 0 for e in nervus_errors)
