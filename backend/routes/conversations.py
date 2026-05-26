"""Conversation lifecycle API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from core.config import get_settings
from services.conversation_service import ConversationService

settings = get_settings()
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def require_auth(x_api_key: Optional[str] = Header(None)) -> None:
    if settings.API_AUTH_TOKEN and x_api_key != settings.API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


@router.post("", dependencies=[Depends(require_auth)])
def create_conversation():
    service = ConversationService()
    return service.create_conversation()


@router.get("", dependencies=[Depends(require_auth)])
def list_conversations():
    service = ConversationService()
    return {"conversations": service.list_conversations()}


@router.get("/{conversation_id}", dependencies=[Depends(require_auth)])
def get_conversation(conversation_id: str):
    service = ConversationService()
    conversation = service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/{conversation_id}/pause", dependencies=[Depends(require_auth)])
def pause_conversation(conversation_id: str):
    service = ConversationService()
    conversation = service.pause_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/{conversation_id}/resume", dependencies=[Depends(require_auth)])
def resume_conversation(conversation_id: str):
    service = ConversationService()
    conversation = service.resume_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}", dependencies=[Depends(require_auth)])
def delete_conversation(conversation_id: str):
    service = ConversationService()
    deleted = service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}
