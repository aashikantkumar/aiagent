"""Secrets storage and validation for API keys."""
from __future__ import annotations

from typing import Any, Optional

import httpx
import psycopg
from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SecretsService:
    """Encrypts and stores provider API keys in PostgreSQL."""

    def __init__(self, dsn: Optional[str] = None, fernet_key: Optional[str] = None) -> None:
        self._dsn = dsn or settings.database_url
        self._fernet_key = fernet_key or settings.SECRETS_FERNET_KEY
        self._fernet: Optional[Fernet] = None

    def _get_fernet(self, require_key: bool) -> Optional[Fernet]:
        if not self._fernet_key:
            if require_key:
                raise ValueError("SECRETS_FERNET_KEY is not set")
            return None
        if self._fernet is None:
            try:
                self._fernet = Fernet(self._fernet_key.encode("utf-8"))
            except Exception as exc:
                raise ValueError("SECRETS_FERNET_KEY is invalid") from exc
        return self._fernet

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn)

    def _ensure_table(self, conn: psycopg.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS secrets (
                provider TEXT PRIMARY KEY,
                secret_encrypted TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        conn.commit()

    def _normalize_provider(self, provider: str) -> str:
        normalized = provider.strip().lower()
        if not normalized:
            raise ValueError("Provider is required")
        return normalized

    def _validate_secret_format(self, provider: str, secret: str) -> None:
        if provider == "groq" and not secret.startswith("gsk_"):
            raise ValueError("Groq keys must start with 'gsk_'")
        if provider == "openai" and not secret.startswith("sk-"):
            raise ValueError("OpenAI keys must start with 'sk-'")
        if provider == "anthropic" and not secret.startswith("sk-ant-"):
            raise ValueError("Anthropic keys must start with 'sk-ant-'")

    def _mask_secret(self, secret: str) -> str:
        if len(secret) <= 8:
            return "***"
        return f"{secret[:2]}...{secret[-4:]}"

    def store_secret(self, provider: str, secret: str) -> dict[str, Any]:
        provider = self._normalize_provider(provider)
        secret = secret.strip()
        if not secret:
            raise ValueError("Secret is required")

        self._validate_secret_format(provider, secret)

        fernet = self._get_fernet(require_key=True)
        encrypted = fernet.encrypt(secret.encode("utf-8")).decode("utf-8")

        with self._connect() as conn:
            self._ensure_table(conn)
            conn.execute(
                """
                INSERT INTO secrets (provider, secret_encrypted)
                VALUES (%s, %s)
                ON CONFLICT (provider)
                DO UPDATE SET secret_encrypted = EXCLUDED.secret_encrypted,
                              updated_at = NOW()
                """,
                (provider, encrypted),
            )
            conn.commit()

        return {"provider": provider, "masked": self._mask_secret(secret)}

    def list_secrets(self) -> list[dict[str, Any]]:
        fernet = self._get_fernet(require_key=True)
        with self._connect() as conn:
            self._ensure_table(conn)
            rows = conn.execute(
                "SELECT provider, secret_encrypted, updated_at FROM secrets ORDER BY provider"
            ).fetchall()

        results: list[dict[str, Any]] = []
        for provider, encrypted, updated_at in rows:
            try:
                secret = fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
            except InvalidToken:
                secret = ""
            results.append(
                {
                    "provider": provider,
                    "masked": self._mask_secret(secret) if secret else "***",
                    "updated_at": updated_at,
                }
            )
        return results

    def get_masked_secret(self, provider: str) -> Optional[dict[str, Any]]:
        provider = self._normalize_provider(provider)
        fernet = self._get_fernet(require_key=True)
        with self._connect() as conn:
            self._ensure_table(conn)
            row = conn.execute(
                "SELECT secret_encrypted, updated_at FROM secrets WHERE provider = %s",
                (provider,),
            ).fetchone()

        if not row:
            return None
        encrypted, updated_at = row
        try:
            secret = fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            secret = ""
        return {
            "provider": provider,
            "masked": self._mask_secret(secret) if secret else "***",
            "updated_at": updated_at,
        }

    def get_secret(self, provider: str, require_key: bool = False) -> Optional[str]:
        provider = self._normalize_provider(provider)
        fernet = self._get_fernet(require_key=require_key)
        if fernet is None:
            return None

        try:
            with self._connect() as conn:
                self._ensure_table(conn)
                row = conn.execute(
                    "SELECT secret_encrypted FROM secrets WHERE provider = %s",
                    (provider,),
                ).fetchone()
        except Exception:
            return None

        if not row:
            return None
        encrypted = row[0]
        try:
            return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Stored secret could not be decrypted") from exc

    def delete_secret(self, provider: str) -> bool:
        provider = self._normalize_provider(provider)
        with self._connect() as conn:
            self._ensure_table(conn)
            result = conn.execute(
                "DELETE FROM secrets WHERE provider = %s",
                (provider,),
            )
            conn.commit()
        return result.rowcount > 0

    def test_secret(self, provider: str, secret: Optional[str] = None) -> dict[str, Any]:
        provider = self._normalize_provider(provider)
        if secret is None:
            secret = self.get_secret(provider, require_key=True)
        if not secret:
            return {"ok": False, "error": "No secret stored for provider"}

        self._validate_secret_format(provider, secret)

        if provider == "groq":
            return self._test_openai_compatible(
                base_url=settings.GROQ_API_BASE_URL,
                secret=secret,
            )
        if provider == "openai":
            return self._test_openai_compatible(
                base_url=settings.OPENAI_API_BASE_URL,
                secret=secret,
            )
        if provider == "anthropic":
            return self._test_anthropic(secret)

        return {"ok": False, "error": "Provider is not supported for testing"}

    def _test_openai_compatible(self, base_url: str, secret: str) -> dict[str, Any]:
        url = f"{base_url.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {secret}"}
        try:
            resp = httpx.get(url, headers=headers, timeout=settings.SECRETS_TEST_TIMEOUT)
            if resp.status_code == 200:
                return {"ok": True, "status_code": resp.status_code}
            return {"ok": False, "status_code": resp.status_code, "error": resp.text}
        except Exception as exc:
            logger.warning("secret_test_failed", provider="openai_compatible", error=str(exc))
            return {"ok": False, "error": "Secret test failed"}

    def _test_anthropic(self, secret: str) -> dict[str, Any]:
        url = f"{settings.ANTHROPIC_API_BASE_URL.rstrip('/')}/models"
        headers = {
            "x-api-key": secret,
            "anthropic-version": settings.ANTHROPIC_API_VERSION,
        }
        try:
            resp = httpx.get(url, headers=headers, timeout=settings.SECRETS_TEST_TIMEOUT)
            if resp.status_code == 200:
                return {"ok": True, "status_code": resp.status_code}
            return {"ok": False, "status_code": resp.status_code, "error": resp.text}
        except Exception as exc:
            logger.warning("secret_test_failed", provider="anthropic", error=str(exc))
            return {"ok": False, "error": "Secret test failed"}
