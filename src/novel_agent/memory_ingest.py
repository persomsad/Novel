"""Ingest continuity index data into NervusDB via CLI."""

from __future__ import annotations

from typing import Any

from . import nervus_cli


def ingest_from_index(
    index: dict[str, Any], db_path: str, *, dry_run: bool = False
) -> dict[str, int]:
    stats = {"characters": 0, "chapters": 0, "events": 0, "references": 0}

    def run(query: str, params: dict[str, Any]) -> None:
        if dry_run:
            return
        nervus_cli.cypher_query(
            db_path,
            query,
            params=params,
            readonly=False,
            format_="json",
        )

    for character in index.get("characters", []):
        stats["characters"] += 1
        run(
            "MERGE (c:Character {id: $id}) SET c.name = $name, c += $props",
            {
                "id": character.get("id"),
                "name": character.get("name"),
                "props": character.get("attributes", {}),
            },
        )

    for chapter in index.get("chapters", []):
        stats["chapters"] += 1
        run(
            "MERGE (ch:Chapter {id: $id}) SET ch.title = $title, ch.summary = $summary",
            {
                "id": chapter.get("chapter_id"),
                "title": chapter.get("title"),
                "summary": chapter.get("summary"),
            },
        )

        for name in chapter.get("characters", []):
            run(
                "MATCH (c:Character {name: $name}), (ch:Chapter {id: $chapter}) "
                "MERGE (c)-[:APPEARS_IN]->(ch)",
                {"name": name, "chapter": chapter.get("chapter_id")},
            )

        for marker in chapter.get("time_markers", []):
            stats["events"] += 1
            event_id = f"{chapter.get('chapter_id')}:{marker.get('line')}"
            run(
                "MATCH (ch:Chapter {id: $chapter}) "
                "MERGE (e:Event {id: $event_id}) "
                "SET e.timestamp = $timestamp, e.context = $context "
                "MERGE (ch)-[:HAS_EVENT]->(e)",
                {
                    "chapter": chapter.get("chapter_id"),
                    "event_id": event_id,
                    "timestamp": marker.get("value"),
                    "context": marker.get("context"),
                },
            )

        for ref in chapter.get("references", []):
            stats["references"] += 1
            run(
                "MERGE (r:Reference {id: $id}) SET r.context = $context "
                "WITH r MATCH (ch:Chapter {id: $chapter}) "
                "MERGE (ch)-[:USES_REFERENCE]->(r)",
                {
                    "id": ref.get("id"),
                    "context": ref.get("context"),
                    "chapter": chapter.get("chapter_id"),
                },
            )

    return stats


__all__ = ["ingest_from_index"]
