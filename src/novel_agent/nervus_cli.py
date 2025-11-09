"""Utility wrappers for invoking the NervusDB CLI via subprocess.

The NervusDB package already ships a powerful CLI (`nervusdb`). Instead of linking
directly against the Node API we spawn the CLI command, which keeps the database
project untouched and lets us swap executables when needed.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Iterable, Sequence


class NervusCLIError(RuntimeError):
    """Raised when the Nervus CLI returns a non-zero exit status."""

    def __init__(self, command: Sequence[str], returncode: int, stdout: str, stderr: str) -> None:
        super().__init__(
            f"Nervus CLI failed (exit code {returncode}). "
            f"Command: {' '.join(command)}\nSTDERR:\n{stderr or '<empty>'}\n"
            f"STDOUT:\n{stdout or '<empty>'}"
        )
        self.command = list(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@dataclass(frozen=True, slots=True)
class NervusCLIConfig:
    """Configuration for running the Nervus CLI."""

    executable: str = os.getenv("NERVUSDB_BIN", "nervusdb")

    def split_executable(self) -> list[str]:
        if not self.executable.strip():
            raise ValueError("Nervus CLI executable path cannot be empty.")
        return shlex.split(self.executable)


def _run_cli(
    subcommand: str,
    args: Iterable[str],
    *,
    config: NervusCLIConfig | None = None,
    input_text: str | None = None,
) -> str:
    cfg = config or NervusCLIConfig()
    command = [*cfg.split_executable(), subcommand, *args]
    result = subprocess.run(
        command,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise NervusCLIError(command, result.returncode, result.stdout, result.stderr)
    return result.stdout.strip()


def cypher_query(
    db_path: str,
    query: str,
    *,
    params: dict[str, Any] | None = None,
    limit: int | None = None,
    optimize: str | None = None,
    format_: str = "json",
    readonly: bool = True,
    config: NervusCLIConfig | None = None,
) -> Any:
    """Run a Cypher query and return the parsed result."""

    cli_args: list[str] = [db_path, "--query", query, "--format", format_]
    if readonly:
        cli_args.append("--readonly")
    if optimize:
        cli_args.append(f"--optimize={optimize}")
    if params:
        cli_args.extend(["--params", json.dumps(params, ensure_ascii=False)])
    if limit is not None:
        cli_args.extend(["--limit", str(limit)])

    output = _run_cli("cypher", cli_args, config=config)
    if format_ == "json":
        if not output:
            return {}
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON returned from Nervus CLI: {output}") from exc
    return output


def stats(db_path: str, *, config: NervusCLIConfig | None = None) -> str:
    """Return the output of `nervusdb stats` for the given database."""

    return _run_cli("stats", [db_path], config=config)


def run_raw(
    subcommand: str,
    args: Iterable[str],
    *,
    config: NervusCLIConfig | None = None,
    input_text: str | None = None,
) -> str:
    """Run an arbitrary Nervus CLI subcommand and return its stdout."""

    return _run_cli(subcommand, list(args), config=config, input_text=input_text)


__all__ = [
    "NervusCLIConfig",
    "NervusCLIError",
    "cypher_query",
    "stats",
    "run_raw",
]
