"""Tests for the continuity index builder."""

from pathlib import Path

from novel_agent import continuity


def test_build_continuity_index(tmp_path: Path) -> None:
    # run against real project tree but write to tmp
    project_root = Path(__file__).resolve().parents[1]
    output_path = tmp_path / "index.json"
    data = continuity.build_continuity_index(project_root, output_path=output_path)

    assert output_path.exists()
    assert len(data["chapters"]) >= 3
    ch1 = next(item for item in data["chapters"] if item["chapter_id"] == "ch001")
    assert "李明" in ch1["characters"]
    assert ch1["time_markers"], "chapter should include time markers"

    references = {ref["id"] for ref in data["references"]}
    assert "childhood-trauma" in references
