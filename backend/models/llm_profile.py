"""LLM profile models."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LLMProfile(BaseModel):
    id: str
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    is_default: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LLMProfileCreate(BaseModel):
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    is_default: bool = False


class LLMProfileUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_default: Optional[bool] = None


class SettingUpdate(BaseModel):
    value: object = Field(..., description="Setting value")
