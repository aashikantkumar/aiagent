"""Secrets management API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from core.config import get_settings
from services.secrets_service import SecretsService

settings = get_settings()
router = APIRouter(prefix="/api/secrets", tags=["secrets"])


def require_auth(x_api_key: Optional[str] = Header(None)) -> None:
    if settings.API_AUTH_TOKEN and x_api_key != settings.API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


class SecretPayload(BaseModel):
    secret: str


class SecretTestPayload(BaseModel):
    secret: Optional[str] = None


@router.get("", dependencies=[Depends(require_auth)])
def list_secrets():
    service = SecretsService()
    try:
        return {"secrets": service.list_secrets()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{provider}", dependencies=[Depends(require_auth)])
def get_secret(provider: str):
    service = SecretsService()
    try:
        data = service.get_masked_secret(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not data:
        raise HTTPException(status_code=404, detail="Secret not found")
    return data


@router.post("/{provider}", dependencies=[Depends(require_auth)])
def store_secret(provider: str, payload: SecretPayload):
    service = SecretsService()
    try:
        return service.store_secret(provider, payload.secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{provider}", dependencies=[Depends(require_auth)])
def delete_secret(provider: str):
    service = SecretsService()
    try:
        deleted = service.delete_secret(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Secret not found")
    return {"deleted": True}


@router.post("/{provider}/test", dependencies=[Depends(require_auth)])
def test_secret(provider: str, payload: SecretTestPayload | None = None):
    service = SecretsService()
    secret = payload.secret if payload else None
    try:
        result = service.test_secret(provider, secret=secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result
