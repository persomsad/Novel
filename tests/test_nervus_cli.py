"""Tests for the NervusDB CLI wrapper."""

from __future__ import annotations

import json
import subprocess
from typing import Any
from unittest import mock

import pytest

from novel_agent import nervus_cli


def _make_completed_process(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


@mock.patch("novel_agent.nervus_cli.subprocess.run")
def test_cypher_query_builds_command(mock_run: mock.Mock) -> None:
    mock_run.return_value = _make_completed_process(stdout=json.dumps({"rows": []}))
    result: Any = nervus_cli.cypher_query(
        db_path="demo.nervusdb",
        query="MATCH (n) RETURN n",
        params={"name": "Alice"},
        limit=5,
    )
    assert result == {"rows": []}
    command = mock_run.call_args[0][0]
    assert command[:4] == ["nervusdb", "cypher", "demo.nervusdb", "--query"]
    assert "--format" in command and "--readonly" in command
    assert "--params" in command
    params_index = command.index("--params") + 1
    assert command[params_index] == json.dumps({"name": "Alice"}, ensure_ascii=False)


@mock.patch("novel_agent.nervus_cli.subprocess.run")
def test_cypher_query_handles_non_json(mock_run: mock.Mock) -> None:
    mock_run.return_value = _make_completed_process(stdout="not-json")
    with pytest.raises(ValueError):
        nervus_cli.cypher_query("demo.nervusdb", "RETURN 1")


@mock.patch("novel_agent.nervus_cli.subprocess.run")
def test_cypher_query_propagates_errors(mock_run: mock.Mock) -> None:
    mock_run.return_value = _make_completed_process(stdout="", stderr="boom", returncode=1)
    with pytest.raises(nervus_cli.NervusCLIError) as excinfo:
        nervus_cli.cypher_query("demo.nervusdb", "RETURN 1")
    assert "boom" in str(excinfo.value)


@mock.patch("novel_agent.nervus_cli.subprocess.run")
def test_stats_returns_stdout(mock_run: mock.Mock) -> None:
    mock_run.return_value = _make_completed_process(stdout="stats output")
    result = nervus_cli.stats("demo.nervusdb")
    assert result == "stats output"
    command = mock_run.call_args[0][0]
    assert command[:3] == ["nervusdb", "stats", "demo.nervusdb"]


@mock.patch("novel_agent.nervus_cli.subprocess.run")
def test_custom_executable(mock_run: mock.Mock) -> None:
    mock_run.return_value = _make_completed_process(stdout=json.dumps({"rows": []}))
    config = nervus_cli.NervusCLIConfig(executable="npx --yes nervusdb")
    nervus_cli.cypher_query("demo.nervusdb", "RETURN 1", config=config)
    command = mock_run.call_args[0][0]
    assert command[0:3] == ["npx", "--yes", "nervusdb"]
