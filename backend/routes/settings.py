"""Settings and LLM profile API endpoints."""
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from core.config import get_settings
from models.llm_profile import LLMProfileCreate, LLMProfileUpdate, SettingUpdate
from services.settings_service import SettingsService

settings = get_settings()
router = APIRouter(prefix="/api/settings", tags=["settings"])


def require_auth(x_api_key: Optional[str] = Header(None)) -> None:
    if settings.API_AUTH_TOKEN and x_api_key != settings.API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


class ResetResponse(BaseModel):
    settings: dict[str, Any]


@router.get("", dependencies=[Depends(require_auth)])
def get_settings():
    service = SettingsService()
    return {"settings": service.get_settings()}


@router.put("/{key}", dependencies=[Depends(require_auth)])
def update_setting(key: str, payload: SettingUpdate):
    service = SettingsService()
    try:
        updated = service.update_setting(key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"updated": updated}


@router.post("/reset", response_model=ResetResponse, dependencies=[Depends(require_auth)])
def reset_settings():
    service = SettingsService()
    return {"settings": service.reset_settings()}


@router.post("/llm-profiles", dependencies=[Depends(require_auth)])
def create_profile(payload: LLMProfileCreate):
    service = SettingsService()
    profile = service.create_profile(payload)
    return profile.model_dump()


@router.get("/llm-profiles", dependencies=[Depends(require_auth)])
def list_profiles():
    service = SettingsService()
    return {"profiles": [p.model_dump() for p in service.list_profiles()]}


@router.get("/llm-profiles/{profile_id}", dependencies=[Depends(require_auth)])
def get_profile(profile_id: str):
    service = SettingsService()
    profile = service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.model_dump()


@router.put("/llm-profiles/{profile_id}", dependencies=[Depends(require_auth)])
def update_profile(profile_id: str, payload: LLMProfileUpdate):
    service = SettingsService()
    profile = service.update_profile(profile_id, payload)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.model_dump()


@router.delete("/llm-profiles/{profile_id}", dependencies=[Depends(require_auth)])
def delete_profile(profile_id: str):
    service = SettingsService()
    deleted = service.delete_profile(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"deleted": True}


@router.post("/llm-profiles/{profile_id}/default", dependencies=[Depends(require_auth)])
def set_default_profile(profile_id: str):
    service = SettingsService()
    try:
        profile = service.set_default_profile(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return profile.model_dump()
