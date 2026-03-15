"""
Audit Logger — append-only log of every agent action.
Default: JSONL file. Swap backend to PostgreSQL by setting AUDIT_DB_URL.
"""

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AuditRecord:
    timestamp: str
    user_id: str
    role: str
    clearance_level: int
    query: str
    response_hash: str          # sha256 of the final response text
    tools_used: list[str]
    data_classifications_accessed: list[int]
    stripped_classifications: list[int]  # levels that were filtered out
    iteration_count: int
    status: str                 # "ok" | "error" | "permission_denied"
    error: str = ""


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()[:16]


def _jsonl_path() -> str:
    return os.path.join(
        os.path.dirname(__file__), "..", "audit.jsonl"
    )


def _write_jsonl(record: AuditRecord) -> None:
    path = _jsonl_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record)) + "\n")


def _write_postgres(record: AuditRecord) -> None:
    """
    PostgreSQL stub — swap in when AUDIT_DB_URL is set.
    Install: pip install psycopg2-binary
    """
    db_url = os.getenv("AUDIT_DB_URL", "")
    if not db_url:
        raise RuntimeError("AUDIT_DB_URL not set")
    try:
        import psycopg2  # type: ignore
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO audit_log
              (timestamp, user_id, role, clearance_level, query, response_hash,
               tools_used, data_classifications_accessed, stripped_classifications,
               iteration_count, status, error)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                record.timestamp, record.user_id, record.role,
                record.clearance_level, record.query, record.response_hash,
                json.dumps(record.tools_used),
                json.dumps(record.data_classifications_accessed),
                json.dumps(record.stripped_classifications),
                record.iteration_count, record.status, record.error,
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        # Audit failure must never block the response — log to file as fallback
        _write_jsonl(record)
        raise RuntimeError(f"Postgres audit failed, fell back to JSONL: {exc}") from exc


class AuditLogger:
    """Write an AuditRecord to the configured backend."""

    def log(
        self,
        *,
        user_id: str,
        role: str,
        clearance_level: int,
        query: str,
        response: str,
        tools_used: list[str],
        data_classifications_accessed: list[int],
        stripped_classifications: list[int],
        iteration_count: int,
        status: str = "ok",
        error: str = "",
    ) -> AuditRecord:
        record = AuditRecord(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            user_id=user_id,
            role=role,
            clearance_level=clearance_level,
            query=query,
            response_hash=_sha256(response),
            tools_used=tools_used,
            data_classifications_accessed=data_classifications_accessed,
            stripped_classifications=stripped_classifications,
            iteration_count=iteration_count,
            status=status,
            error=error,
        )
        if os.getenv("AUDIT_DB_URL"):
            _write_postgres(record)
        else:
            _write_jsonl(record)
        return record


# Module-level singleton
logger = AuditLogger()
