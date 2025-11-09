from pathlib import Path
from unittest import mock

from novel_agent import continuity, memory_ingest


@mock.patch("novel_agent.memory_ingest.nervus_cli.cypher_query")
def test_ingest_from_index_calls_cli(mock_cypher: mock.Mock) -> None:
    project_root = Path(__file__).resolve().parents[1]
    data = continuity.build_continuity_index(project_root)
    stats = memory_ingest.ingest_from_index(data, db_path="demo.nervusdb")

    assert stats["characters"] >= 2
    assert mock_cypher.called


@mock.patch("novel_agent.memory_ingest.nervus_cli.cypher_query")
def test_ingest_dry_run(mock_cypher: mock.Mock) -> None:
    project_root = Path(__file__).resolve().parents[1]
    data = continuity.build_continuity_index(project_root)
    stats = memory_ingest.ingest_from_index(data, db_path="demo.nervusdb", dry_run=True)
    assert stats["chapters"] >= 3
    mock_cypher.assert_not_called()
