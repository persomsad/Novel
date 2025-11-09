"""Utilities for building structured continuity indexes from project files."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

TIME_PATTERN = re.compile(r"\[TIME:([^\]]+)\]\s*(.*)")
REF_PATTERN = re.compile(r"\[REF:([^\]]+)\]")


@dataclass(slots=True)
class ChapterEntry:
    chapter_id: str
    title: str
    path: str
    characters: list[str]
    summary: str
    time_markers: list[dict[str, Any]]
    references: list[dict[str, Any]]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "item"


def _load_character_profiles(root: Path) -> list[dict[str, Any]]:
    profiles_path = root / "spec" / "knowledge" / "character-profiles.md"
    if not profiles_path.exists():
        return []

    profiles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in profiles_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("## "):
            name = line.split("：", 1)[-1].strip()
            current = {
                "id": _slugify(name),
                "name": name,
                "attributes": {},
            }
            profiles.append(current)
        elif line.startswith("- **") and current is not None:
            parts = line.split("：", 1)
            if len(parts) == 2:
                key = parts[0].strip("- *")
                value = parts[1].strip()
                current["attributes"][key] = value
    return profiles


def _chapter_summary(text_lines: list[str]) -> str:
    for line in text_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            summary = stripped.replace("\n", " ")
            return summary[:200]
    return ""


def _extract_time_markers(lines: list[str]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        match = TIME_PATTERN.search(line)
        if match:
            markers.append(
                {
                    "value": match.group(1).strip(),
                    "context": match.group(2).strip(),
                    "line": idx,
                }
            )
    return markers


def _extract_references(lines: list[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        for match in REF_PATTERN.finditer(line):
            refs.append({"id": match.group(1).strip(), "line": idx, "context": line.strip()})
    return refs


def _detect_characters(text: str, character_names: Iterable[str]) -> list[str]:
    present = []
    for name in character_names:
        if name and name in text:
            present.append(name)
    return present


def build_continuity_index(
    root: Path | str = Path("."),
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    root_path = Path(root)
    characters = _load_character_profiles(root_path)
    character_names = [c["name"] for c in characters]
    chapters_dir = root_path / "chapters"
    chapters: list[ChapterEntry] = []

    for file_path in sorted(chapters_dir.glob("*.md")):
        lines = file_path.read_text(encoding="utf-8").splitlines()
        text = "\n".join(lines)
        title = next((line.lstrip("# ") for line in lines if line.startswith("#")), file_path.stem)
        chapter_id = file_path.stem
        entry = ChapterEntry(
            chapter_id=chapter_id,
            title=title.strip(),
            path=str(file_path.relative_to(root_path)),
            characters=_detect_characters(text, character_names),
            summary=_chapter_summary(lines),
            time_markers=_extract_time_markers(lines),
            references=_extract_references(lines),
        )
        chapters.append(entry)

    reference_index: dict[str, list[dict[str, Any]]] = {}
    for chapter in chapters:
        for ref in chapter.references:
            reference_index.setdefault(ref["id"], []).append(
                {
                    "chapter_id": chapter.chapter_id,
                    "line": ref["line"],
                    "context": ref["context"],
                }
            )

    data = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "chapters": [asdict(chapter) for chapter in chapters],
        "characters": characters,
        "references": [
            {"id": ref_id, "occurrences": occurrences}
            for ref_id, occurrences in sorted(reference_index.items())
        ],
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return data
