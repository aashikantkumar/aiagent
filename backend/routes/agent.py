"""
Agent routes — WebSocket streaming + HTTP endpoints for session management.

This module owns all the agent-facing API surface. The WebSocket endpoint
streams LangGraph events to the frontend, and the HTTP endpoints let the
frontend query session status, list sessions, etc.
"""
import uuid
import asyncio
import time
import os
import tempfile
from collections import deque
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query, UploadFile, File, Response
from pydantic import BaseModel as PydanticBaseModel
from langchain_core.messages import HumanMessage

from core.config import get_settings
from core.logger import get_logger
from services.settings_service import SettingsService
from services.conversation_service import ConversationService
from services.sandbox_service import SandboxService

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/agent", tags=["agent"])

PING_INTERVAL = 10
PING_TIMEOUT = 120  # 2 minutes — allows for rate-limit backoff waits
MAX_EVENT_BUFFER = 1000


class _EventBuffer:
    def __init__(self, max_size: int = MAX_EVENT_BUFFER) -> None:
        self._max_size = max_size
        self._buffers: dict[str, deque[dict]] = {}
        self._seq: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def add(self, session_id: str, payload: dict) -> int:
        async with self._lock:
            seq = self._seq.get(session_id, 0) + 1
            self._seq[session_id] = seq
            buf = self._buffers.setdefault(session_id, deque(maxlen=self._max_size))
            item = {**payload, "seq": seq}
            buf.append(item)
            return seq

    async def replay_after(self, session_id: str, last_seq: int) -> list[dict]:
        async with self._lock:
            buf = list(self._buffers.get(session_id, deque()))
        return [item for item in buf if item.get("seq", 0) > last_seq]


EVENT_BUFFER = _EventBuffer()


class CreateSessionRequest(PydanticBaseModel):
    profile_id: str | None = None


# ── Helpers ─────────────────────────────────────────────────────────────

def serialize_data(data):
    """Recursively serialize Pydantic models and LangChain messages for JSON."""
    if isinstance(data, PydanticBaseModel):
        return data.model_dump()
    if isinstance(data, dict):
        return {k: serialize_data(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [serialize_data(v) for v in data]
    # Handle LangChain messages gracefully
    if hasattr(data, 'content') and hasattr(data, 'type'):
        return {'type': data.type, 'content': data.content}
    return data


# ── HTTP Endpoints ──────────────────────────────────────────────────────

@router.get("/health")
async def health():
    """Quick health-check for the agent subsystem."""
    return {"status": "ok", "version": settings.APP_VERSION}


@router.get("/groq/stats")
async def groq_key_stats():
    """Get Groq API key pool statistics — useful for monitoring rate limits."""
    try:
        from agent.groq_key_pool import get_groq_pool
        pool = get_groq_pool()
        return {
            "pool_size": pool.size,
            "keys": pool.get_stats(),
            "provider": settings.DEFAULT_LLM_PROVIDER,
            "model": settings.DEFAULT_LLM_MODEL,
        }
    except Exception as e:
        return {"error": str(e), "pool_size": 0, "keys": []}


@router.post("/sessions")
async def create_session(payload: CreateSessionRequest | None = None):
    """Create a new agent session and return its ID."""
    conversation_service = ConversationService()
    try:
        conversation = conversation_service.create_conversation()
        session_id = conversation["id"]
    except Exception as exc:
        logger.warning("conversation_create_failed", error=str(exc))
        conversation = None
        session_id = str(uuid.uuid4())

    logger.info("session_created", session_id=session_id)

    # Get LLM profile (from request or default)
    service = SettingsService()
    profile = None
    if payload and payload.profile_id:
        profile = service.get_profile(payload.profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")
    else:
        profile = service.get_default_profile()

    # If no profile found, create a default one using current settings
    if profile is None:
        logger.info("no_default_profile_using_settings", session_id=session_id)

    response = {"session_id": session_id}
    if conversation:
        response["conversation"] = conversation
    if profile:
        response["profile_id"] = profile.id
        response["profile"] = profile.model_dump()
    return response


# ── WebSocket Endpoint ──────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Main agent communication channel.

    The frontend sends a JSON payload:
        { "session_id": "...", "message": "..." }

    The backend streams LangGraph events back as JSON frames.
    """
    await ws.accept()
    session_id = "unknown"

    last_pong = time.time()
    receive_task = None
    ping_task = None

    async def receive_loop():
        nonlocal last_pong
        while True:
            try:
                msg = await ws.receive_json()
            except WebSocketDisconnect:
                break
            except Exception:
                break

            msg_type = msg.get("type")
            if msg_type == "pong":
                last_pong = time.time()
                continue
            if msg_type == "ping":
                await ws.send_json({"type": "pong", "ts": msg.get("ts")})
                last_pong = time.time()
                continue

    async def ping_loop():
        while True:
            await asyncio.sleep(PING_INTERVAL)
            if time.time() - last_pong > PING_TIMEOUT:
                logger.info("ws_ping_timeout", session_id=session_id)
                try:
                    await ws.close(code=1001)
                except Exception:
                    pass
                break
            try:
                await ws.send_json({"type": "ping", "ts": time.time()})
            except Exception:
                break

    try:
        data = await ws.receive_json()
        session_id = data.get("session_id", str(uuid.uuid4()))
        message = data.get("message", "")
        profile_id = data.get("profile_id")
        last_seq = int(data.get("last_seq") or 0)

        # Get LLM profile
        settings_service = SettingsService()
        profile = None
        if profile_id:
            profile = settings_service.get_profile(profile_id)
        if profile is None:
            profile = settings_service.get_default_profile()

        logger.info("ws_session_start", session_id=session_id)

        # Mark conversation as active
        conversation_service = ConversationService()
        try:
            conversation_service.mark_active(session_id)
        except Exception as exc:
            logger.warning("conversation_mark_active_failed", session_id=session_id, error=str(exc))

        # Lazy import to avoid circular deps — graph is built once per worker
        from agent.graph import get_graph
        graph = await get_graph()

        # Set recursion limit to 100 to allow building complete applications
        # Default is 25, but complex apps need more iterations
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 100
        }

        replay_events = await EVENT_BUFFER.replay_after(session_id, last_seq)
        for event in replay_events:
            await ws.send_json({**event, "replay": True})

        state = {
            "messages": [HumanMessage(content=message)],
            "retries": 0,
            "files": {},
            "last_obs": None,
            "session_id": session_id,
            "llm_profile": profile.model_dump() if profile else None,
        }

        last_pong = time.time()
        receive_task = asyncio.create_task(receive_loop())
        ping_task = asyncio.create_task(ping_loop())

        # Stream LangGraph events
        async for event in graph.astream_events(state, config, version="v2"):
            if event["event"] in [
                "on_chain_start",
                "on_chain_end",
                "on_chat_model_stream",
                "on_tool_end",
            ]:
                chunk = ""
                if event["event"] == "on_chat_model_stream":
                    chunk_obj = event.get("data", {}).get("chunk")
                    chunk = getattr(chunk_obj, "content", "") if chunk_obj else ""
                    if not chunk:
                        continue

                serialized_data = serialize_data(event.get("data"))

                payload = {
                    "type": event["event"],
                    "node": event.get("name"),
                    "data": serialized_data,
                    "chunk": chunk,
                }
                seq = await EVENT_BUFFER.add(session_id, payload)
                
                try:
                    await ws.send_json({**payload, "seq": seq})
                except (RuntimeError, WebSocketDisconnect):
                    logger.info("ws_client_stopped_generation", session_id=session_id)
                    break

    except WebSocketDisconnect:
        logger.info("ws_disconnected", session_id=session_id)
        try:
            ConversationService().pause_conversation(session_id)
        except Exception:
            pass
    except Exception as e:
        logger.error("ws_error", session_id=session_id, error=str(e), exc_info=True)
        try:
            await ws.send_json({
                "type": "error",
                "error": str(e),
                "message": f"Execution error: {str(e)}"
            })
        except Exception:
            pass
        try:
            await ws.close(code=1011)
        except Exception:
            pass
    finally:
        for task in (receive_task, ping_task):
            if task:
                task.cancel()


# ── Sandbox Management Endpoints (OpenHands-style) ──────────────────────

@router.get("/sandboxes")
async def list_sandboxes():
    """Get all tracked sandboxes across the application."""
    try:
        service = SandboxService()
        sandboxes = await service.list_all()
        return {"sandboxes": [s.model_dump() for s in sandboxes]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{session_id}/status")
async def sandbox_status(session_id: str):
    """Get the current status of a sandbox container."""
    try:
        service = SandboxService()
        info = await service.get_status(session_id)
        return info.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{session_id}/health")
async def sandbox_health(session_id: str, port: int = 3000):
    """Health-check: is the app running inside the sandbox?"""
    try:
        service = SandboxService()
        result = await service.health(session_id, port=port)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{session_id}/files")
async def sandbox_files(session_id: str):
    """List generated files in the sandbox workspace."""
    try:
        service = SandboxService()
        return {"files": await service.list_files(session_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{session_id}/files/read")
async def sandbox_file_read(session_id: str, path: str = Query(...)):
    """Read one generated text file from the sandbox workspace."""
    try:
        service = SandboxService()
        return {"path": path, "content": await service.read_file(session_id, path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{session_id}/download")
async def sandbox_download(session_id: str):
    """Download the entire workspace as a ZIP file."""
    try:
        service = SandboxService()
        zip_bytes = await service.download_workspace(session_id)
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=workspace_{session_id[:8]}.zip"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sandbox/{session_id}/pause")
async def sandbox_pause(session_id: str):
    """Pause a running sandbox (frees CPU, preserves state)."""
    try:
        service = SandboxService()
        success = await service.pause(session_id)
        return {"paused": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sandbox/{session_id}/resume")
async def sandbox_resume(session_id: str):
    """Resume a paused sandbox."""
    try:
        service = SandboxService()
        success = await service.resume(session_id)
        return {"resumed": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sandbox/{session_id}/usage")
async def sandbox_usage(session_id: str):
    """Get sandbox container CPU and memory usage."""
    try:
        service = SandboxService()
        return await service.usage(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sandbox/{session_id}")
async def sandbox_delete(session_id: str):
    """Stop and remove a sandbox container."""
    try:
        service = SandboxService()
        await service.delete(session_id)
        return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Document Upload & RAG Endpoints ─────────────────────────────────────

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    enable_rag: bool = True,
):
    """
    Upload an SRS document (PDF, DOCX, MD, TXT) for processing.

    If RAG is enabled and dependencies are available, the document will be
    chunked, embedded, and indexed for semantic search during agent planning.
    """
    # Validate file type
    allowed_extensions = {".pdf", ".docx", ".doc", ".md", ".txt", ".markdown"}
    filename = file.filename or "upload.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(allowed_extensions))}",
        )

    # Save to temp file
    tmp_path: str | None = None
    try:
        suffix = ext
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Process the document
        from agent.srs_loader import load_srs_with_rag

        result = load_srs_with_rag(tmp_path, enable_rag=enable_rag)

        logger.info(
            "document_uploaded",
            file_name=filename,
            text_length=len(result["text"]),
            chunks=result["chunks"],
            rag=result["rag_enabled"],
        )

        return {
            "filename": filename,
            "document_id": result["document_id"],
            "text_length": len(result["text"]),
            "text_preview": result["text"][:500],
            "full_text": result["text"],
            "chunks_indexed": result["chunks"],
            "rag_enabled": result["rag_enabled"],
        }

    except Exception as e:
        logger.error("document_upload_failed", file_name=filename, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@router.get("/rag/search")
async def rag_search(
    query: str = Query(..., description="Search query"),
    document_id: str = Query(None, description="Filter by document ID"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results"),
):
    """Search indexed documents using semantic similarity."""
    try:
        from agent.embedding_engine import EmbeddingEngine

        engine = EmbeddingEngine()
        results = engine.search(query, top_k=top_k, document_id=document_id)
        return {"query": query, "results": results, "count": len(results)}
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="RAG dependencies not installed. Install: pip install sentence-transformers chromadb",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/sandbox/{session_id}/terminal")
async def sandbox_terminal(ws: WebSocket, session_id: str):
    """WebSocket endpoint for raw interactive shell access to the container."""
    await ws.accept()
    
    try:
        from services.sandbox_service import SandboxService
        service = SandboxService()
        runtime = await service.get_runtime(session_id)
        container_name = runtime.container_name
    except Exception as e:
        await ws.send_json({"type": "output", "data": f"\r\nError connecting to sandbox: {str(e)}\r\n"})
        await ws.close()
        return

    import pty
    import os
    import subprocess
    import fcntl
    import termios
    import struct

    # Open pseudo-terminal
    master_fd, slave_fd = pty.openpty()
    
    # Spawn docker exec inside the pty
    p = subprocess.Popen(
        ["docker", "exec", "-it", container_name, "/bin/bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)

    output_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def read_callback():
        try:
            data = os.read(master_fd, 4096)
            if not data:
                loop.call_soon_threadsafe(output_queue.put_nowait, None)
                return
            loop.call_soon_threadsafe(output_queue.put_nowait, data)
        except Exception:
            loop.call_soon_threadsafe(output_queue.put_nowait, None)

    loop.add_reader(master_fd, read_callback)

    async def write_loop():
        try:
            while True:
                msg = await ws.receive_json()
                msg_type = msg.get("type")
                if msg_type == "input":
                    data = msg.get("data", "")
                    if data:
                        os.write(master_fd, data.encode("utf-8"))
                elif msg_type == "resize":
                    cols = msg.get("cols", 80)
                    rows = msg.get("rows", 24)
                    try:
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            # Signal the read loop to stop by putting None
            await output_queue.put(None)

    write_task = asyncio.create_task(write_loop())

    try:
        while True:
            data = await output_queue.get()
            if data is None:
                break
            # Send raw terminal output back as JSON
            await ws.send_json({"type": "output", "data": data.decode("utf-8", errors="replace")})
    except Exception:
        pass
    finally:
        # Cleanup
        write_task.cancel()
        loop.remove_reader(master_fd)
        try:
            os.close(master_fd)
        except Exception:
            pass
        
        # Terminate subprocess
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=1)
            except subprocess.TimeoutExpired:
                p.kill()
        
        try:
            await ws.close()
        except Exception:
            pass

