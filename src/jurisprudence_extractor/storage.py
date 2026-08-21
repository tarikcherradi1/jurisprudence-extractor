from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Self

from .models import JudicialDecision


class DecisionStore:
    def __init__(self, path: str | Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                stable_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                decision_number TEXT,
                case_number TEXT,
                decision_date TEXT,
                content_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )

    def save(self, decision: JudicialDecision) -> bool:
        item = decision if decision.content_sha256 else decision.with_fingerprint()
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO decisions
            (stable_key, source, decision_number, case_number, decision_date,
             content_sha256, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.stable_key,
                item.source,
                item.decision_number,
                item.case_number,
                item.decision_date.isoformat() if item.decision_date else None,
                item.content_sha256,
                json.dumps(item.model_dump(mode="json"), ensure_ascii=False),
            ),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
