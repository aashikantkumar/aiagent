"""Conversation lifecycle management."""
from __future__ import annotations

import uuid
from typing import Any, Optional

import psycopg

from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ConversationService:
    """Stores conversation lifecycle metadata in PostgreSQL."""

    def __init__(self, dsn: Optional[str] = None) -> None:
        self._dsn = dsn or settings.database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn)

    def _ensure_table(self, conn: psycopg.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id UUID PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        conn.commit()

    def _row_to_conversation(self, row: tuple[Any, ...]) -> dict[str, Any]:
        conversation_id, status, created_at, updated_at = row
        return {
            "id": str(conversation_id),
            "status": status,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }

    def create_conversation(self) -> dict[str, Any]:
        conversation_id = uuid.uuid4()
        with self._connect() as conn:
            self._ensure_table(conn)
            conn.execute(
                """
                INSERT INTO conversations (id, status)
                VALUES (%s, %s)
                """,
                (conversation_id, "active"),
            )
            conn.commit()

        return self.get_conversation(str(conversation_id)) or {
            "id": str(conversation_id),
            "status": "active",
            "created_at": None,
            "updated_at": None,
        }

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            self._ensure_table(conn)
            rows = conn.execute(
                """
                SELECT id, status, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._row_to_conversation(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            self._ensure_table(conn)
            row = conn.execute(
                """
                SELECT id, status, created_at, updated_at
                FROM conversations
                WHERE id = %s
                """,
                (conversation_id,),
            ).fetchone()
        return self._row_to_conversation(row) if row else None

    def mark_active(self, conversation_id: str) -> Optional[dict[str, Any]]:
        return self._update_status(conversation_id, "active")

    def pause_conversation(self, conversation_id: str) -> Optional[dict[str, Any]]:
        return self._update_status(conversation_id, "paused")

    def resume_conversation(self, conversation_id: str) -> Optional[dict[str, Any]]:
        return self._update_status(conversation_id, "active")

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as conn:
            self._ensure_table(conn)
            result = conn.execute(
                "DELETE FROM conversations WHERE id = %s",
                (conversation_id,),
            )
            conn.commit()
        return result.rowcount > 0

    def _update_status(self, conversation_id: str, status: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            self._ensure_table(conn)
            conn.execute(
                """
                UPDATE conversations
                SET status = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (status, conversation_id),
            )
            conn.commit()
        return self.get_conversation(conversation_id)
