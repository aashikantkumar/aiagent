"""
Docker Sandbox Runtime — inspired by OpenHands' DockerSandboxService.

Features ported from OpenHands:
  - Health checks (ping the container to verify the app is alive)
  - Exposed port management (dynamic port mapping for frontend preview)
  - Container lifecycle (pause / resume / delete)
  - Max sandbox limits (auto-cleans old sandboxes)
  - Init process (proper signal handling and zombie process reaping)
  - Status tracking (STARTING → RUNNING → PAUSED → ERROR → MISSING)
"""
import docker
import tarfile
import zipfile
import io
import time
import json
import socket
import re as re_mod
import pexpect
import asyncio
import redis
import httpx
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from agent.schema import CmdRunAction, FileWriteAction, FileReadAction, BrowserAction, ActionType
from browser import PlaywrightManager
from core.config import get_settings
from core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


# ── Redis singleton ─────────────────────────────────────────────────────

_redis: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    return _redis


# ── Sandbox models (inspired by OpenHands SandboxInfo) ──────────────────

class SandboxStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    MISSING = "missing"


class ExposedPort(BaseModel):
    name: str
    container_port: int
    host_port: int = 0  # 0 = auto-assigned


class SandboxInfo(BaseModel):
    session_id: str
    container_name: str
    container_ip: str = "127.0.0.1"
    status: SandboxStatus = SandboxStatus.STARTING
    exposed_ports: List[ExposedPort] = []
    created_at: float = 0.0


# ── Port helper ─────────────────────────────────────────────────────────

def _find_unused_port() -> int:
    """Find an unused port on the host machine (same approach as OpenHands)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        return s.getsockname()[1]


# ── Docker status mapping (from OpenHands) ──────────────────────────────

_DOCKER_STATUS_MAP = {
    'running': SandboxStatus.RUNNING,
    'paused': SandboxStatus.PAUSED,
    'exited': SandboxStatus.PAUSED,
    'created': SandboxStatus.STARTING,
    'restarting': SandboxStatus.STARTING,
    'removing': SandboxStatus.MISSING,
    'dead': SandboxStatus.ERROR,
}


class DockerRuntime:
    """
    Manages a sandboxed Docker container with a persistent bash shell.

    Inspired by OpenHands' DockerSandboxService, this class adds:
    - Health checks for the running app
    - Dynamic port exposure for frontend previews
    - Pause / resume / delete lifecycle management
    - Max sandbox limits with automatic cleanup
    - `init=True` for proper signal handling
    """

    _local_cache: Dict[str, 'DockerRuntime'] = {}
    REDIS_KEY_PREFIX = "agent:sandbox:"
    MAX_SANDBOXES = 5
    HEALTH_CHECK_TIMEOUT = 5  # seconds

    # Default ports exposed from the sandbox container
    DEFAULT_EXPOSED_PORTS = [
        ExposedPort(name="app_server", container_port=3000),
        ExposedPort(name="dev_server", container_port=5173),
        ExposedPort(name="backend", container_port=8000),
    ]

    # ── Factory ─────────────────────────────────────────────────────────

    @classmethod
    def get(cls, session_id: str) -> 'DockerRuntime':
        # 1. In-process cache
        if session_id in cls._local_cache:
            rt = cls._local_cache[session_id]
            try:
                rt.container.reload()
                if rt.container.status == 'running':
                    return rt
            except Exception:
                logger.warning("container_stale", session_id=session_id)
                cls._local_cache.pop(session_id, None)

        # 2. Redis lookup
        r = _get_redis()
        stored = r.get(f"{cls.REDIS_KEY_PREFIX}{session_id}")
        if stored:
            meta = json.loads(stored)
            container_name = meta.get("container_name")
            try:
                client = docker.from_env()
                container = client.containers.get(container_name)
                if container.status in ('running', 'paused'):
                    # Resume if paused
                    if container.status == 'paused':
                        container.unpause()
                        logger.info("container_resumed", session_id=session_id)

                    logger.info("container_reattach", session_id=session_id, container=container_name)
                    rt = cls.__new__(cls)
                    rt.session_id = session_id
                    rt.client = client
                    rt.container = container
                    rt.container_name = container_name
                    rt.container_ip = meta.get("container_ip", "127.0.0.1")
                    rt.exposed_ports = [ExposedPort(**p) for p in meta.get("exposed_ports", [])]
                    rt._init_shell()
                    cls._local_cache[session_id] = rt
                    return rt
            except docker.errors.NotFound:
                logger.warning("container_gone", session_id=session_id, container=container_name)
                r.delete(f"{cls.REDIS_KEY_PREFIX}{session_id}")

        # 3. Enforce max sandbox limit before creating new one
        cls._enforce_sandbox_limit()

        # 4. Create brand-new sandbox
        rt = cls(session_id)
        cls._local_cache[session_id] = rt
        return rt

    # ── Sandbox limit enforcement (from OpenHands) ──────────────────────

    @classmethod
    def _enforce_sandbox_limit(cls):
        """Pause oldest sandboxes if we've hit the limit."""
        r = _get_redis()
        keys = r.keys(f"{cls.REDIS_KEY_PREFIX}*")
        if len(keys) < cls.MAX_SANDBOXES:
            return

        entries = []
        for key in keys:
            raw = r.get(key)
            if raw:
                meta = json.loads(raw)
                entries.append((key, meta))

        entries.sort(key=lambda e: e[1].get("created_at", 0))

        to_pause = len(entries) - (cls.MAX_SANDBOXES - 1)
        client = docker.from_env()
        for key, meta in entries[:to_pause]:
            try:
                container = client.containers.get(meta["container_name"])
                if container.status == 'running':
                    container.pause()
                    logger.info("container_auto_paused", container=meta["container_name"])
            except Exception:
                pass

    @classmethod
    def cleanup_old(cls, max_age_seconds: int = 86400) -> int:
        """Remove sandboxes older than the max age."""
        r = _get_redis()
        keys = r.keys(f"{cls.REDIS_KEY_PREFIX}*")
        if not keys:
            return 0

        now = time.time()
        client = docker.from_env()
        removed = 0
        for key in keys:
            raw = r.get(key)
            if not raw:
                continue
            meta = json.loads(raw)
            created_at = meta.get("created_at", 0)
            if not created_at or (now - created_at) < max_age_seconds:
                continue
            container_name = meta.get("container_name")
            try:
                container = client.containers.get(container_name)
                container.stop(timeout=10)
                container.remove()
                removed += 1
                logger.info("container_auto_removed", container=container_name)
            except docker.errors.NotFound:
                pass
            except Exception as e:
                logger.warning("container_cleanup_failed", container=container_name, error=str(e))
            r.delete(key)
        return removed

    @classmethod
    def list_all(cls) -> List[SandboxInfo]:
        """List all tracked sandboxes from Redis and Docker."""
        r = _get_redis()
        keys = r.keys(f"{cls.REDIS_KEY_PREFIX}*")
        sandboxes = []
        if not keys:
            return sandboxes
            
        client = docker.from_env()
        for key in keys:
            raw = r.get(key)
            if not raw:
                continue
            meta = json.loads(raw)
            session_id = key[len(cls.REDIS_KEY_PREFIX):]
            container_name = meta.get("container_name")
            
            try:
                container = client.containers.get(container_name)
                docker_status = container.status
                status = _DOCKER_STATUS_MAP.get(docker_status, SandboxStatus.ERROR)
            except Exception:
                status = SandboxStatus.MISSING
                
            sandboxes.append(SandboxInfo(
                session_id=session_id,
                container_name=container_name or "unknown",
                container_ip=meta.get("container_ip", "127.0.0.1"),
                status=status,
                exposed_ports=[ExposedPort(**p) for p in meta.get("exposed_ports", [])],
                created_at=meta.get("created_at", 0)
            ))
            
        # Sort by most recently created
        sandboxes.sort(key=lambda s: s.created_at, reverse=True)
        return sandboxes

    # ── Constructor ─────────────────────────────────────────────────────

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.client = docker.from_env()

        try:
            self.client.images.get(settings.SANDBOX_IMAGE)
        except docker.errors.ImageNotFound:
            logger.error("sandbox_image_missing", image=settings.SANDBOX_IMAGE)
            raise RuntimeError(f"Docker image '{settings.SANDBOX_IMAGE}' not found. Build it first.")

        self.container_name = f"agent-sandbox-{session_id[:8]}-{int(time.time())}"
        logger.info("container_start", session_id=session_id, container=self.container_name)

        # Assign host ports for each exposed port (like OpenHands)
        self.exposed_ports = []
        port_bindings = {}
        for ep in self.DEFAULT_EXPOSED_PORTS:
            host_port = _find_unused_port()
            self.exposed_ports.append(ExposedPort(
                name=ep.name,
                container_port=ep.container_port,
                host_port=host_port,
            ))
            port_bindings[f"{ep.container_port}/tcp"] = host_port

        import os
        # Create a workspace directory on the host for this session
        host_workspace_dir = os.path.abspath(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspaces", session_id)
        )
        os.makedirs(host_workspace_dir, exist_ok=True)

        self.container = self.client.containers.run(
            settings.SANDBOX_IMAGE,
            command='sleep infinity',
            detach=True,
            working_dir='/workspace',
            mem_limit=settings.SANDBOX_MEM_LIMIT,
            cpu_period=100000,
            cpu_quota=settings.SANDBOX_CPU_QUOTA,
            name=self.container_name,
            # OpenHands key features:
            init=True,       # proper signal handling & zombie reaping
            remove=False,    # allow pause/resume (can't pause auto-remove containers)
            ports=port_bindings,
            extra_hosts={"host.docker.internal": "host-gateway"},
            volumes={
                host_workspace_dir: {
                    'bind': '/workspace',
                    'mode': 'rw'
                }
            }
        )

        time.sleep(1)
        self.container.reload()
        self.container_ip = (
            self.container.attrs
            .get('NetworkSettings', {})
            .get('IPAddress', '127.0.0.1')
        )

        # Persist to Redis
        r = _get_redis()
        r.set(
            f"{self.REDIS_KEY_PREFIX}{session_id}",
            json.dumps({
                "container_name": self.container_name,
                "container_ip": self.container_ip,
                "exposed_ports": [ep.model_dump() for ep in self.exposed_ports],
                "created_at": time.time(),
            }),
            ex=86400,
        )

        self._init_shell()

    # ── Shell ───────────────────────────────────────────────────────────

    def _init_shell(self):
        """Spawn a persistent interactive bash session inside the container."""
        self.shell = pexpect.spawn(
            f'docker exec -it {self.container_name} /bin/bash',
            encoding='utf-8',
        )
        self.shell.sendline('export PS1="[PROMPT_END]# "')
        self.shell.expect('\\[PROMPT_END\\]# ', timeout=5)

    # ── Health check (from OpenHands) ───────────────────────────────────

    async def health_check(self, port: int = 3000) -> dict:
        """
        Check if an app is running on the given port inside the sandbox.
        Returns status and HTTP response code.
        """
        host_port = None
        for ep in self.exposed_ports:
            if ep.container_port == port:
                host_port = ep.host_port
                break

        if host_port is None:
            return {"healthy": False, "error": f"Port {port} not exposed"}

        try:
            async with httpx.AsyncClient(timeout=self.HEALTH_CHECK_TIMEOUT) as client:
                resp = await client.get(f"http://localhost:{host_port}/")
                return {
                    "healthy": resp.status_code < 500,
                    "status_code": resp.status_code,
                    "url": f"http://localhost:{host_port}",
                }
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    # ── Status (from OpenHands) ─────────────────────────────────────────

    def get_status(self) -> SandboxInfo:
        """Get the current sandbox status."""
        try:
            self.container.reload()
            docker_status = self.container.status
            status = _DOCKER_STATUS_MAP.get(docker_status, SandboxStatus.ERROR)
        except Exception:
            status = SandboxStatus.MISSING

        return SandboxInfo(
            session_id=self.session_id,
            container_name=self.container_name,
            container_ip=self.container_ip,
            status=status,
            exposed_ports=self.exposed_ports,
        )

    def get_resource_usage(self) -> dict:
        """Return container CPU and memory usage."""
        try:
            stats = self.container.stats(stream=False)
            cpu_total = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
            cpu_prev = stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
            sys_total = stats.get("cpu_stats", {}).get("system_cpu_usage", 0)
            sys_prev = stats.get("precpu_stats", {}).get("system_cpu_usage", 0)
            cpu_delta = cpu_total - cpu_prev
            sys_delta = sys_total - sys_prev
            percpu = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("percpu_usage") or []
            cpu_count = max(len(percpu), 1)
            cpu_percent = (cpu_delta / sys_delta) * cpu_count * 100 if sys_delta > 0 else 0.0

            mem_usage = stats.get("memory_stats", {}).get("usage", 0)
            mem_limit = stats.get("memory_stats", {}).get("limit", 0)
            mem_percent = (mem_usage / mem_limit) * 100 if mem_limit else 0.0

            return {
                "cpu_percent": round(cpu_percent, 2),
                "mem_usage": mem_usage,
                "mem_limit": mem_limit,
                "mem_percent": round(mem_percent, 2),
            }
        except Exception as e:
            logger.error("container_stats_error", session_id=self.session_id, error=str(e))
            return {"error": "Unable to read container stats"}

    def list_files(self, max_depth: int = 5) -> list[str]:
        """List workspace files inside the sandbox."""
        result = self.container.exec_run(
            [
                "find",
                "/workspace",
                "-maxdepth",
                str(max_depth),
                "(",
                "-name", "node_modules",
                "-o", "-name", ".git",
                "-o", "-name", "venv",
                "-o", "-name", ".venv",
                "-o", "-name", ".agents",
                "-o", "-name", ".codex",
                ")",
                "-prune",
                "-o",
                "-type",
                "f",
                "-printf",
                "%P\n",
            ]
        )
        if result.exit_code != 0:
            output = result.output.decode("utf-8", errors="replace")
            raise RuntimeError(output.strip() or "Failed to list workspace files")
        output = result.output.decode("utf-8", errors="replace")
        return sorted(path for path in output.splitlines() if path.strip())

    def read_file(self, path: str) -> str:
        """Read one UTF-8 text file from the sandbox workspace."""
        safe_path = path.strip().lstrip("/")
        if not safe_path or ".." in safe_path.split("/"):
            raise ValueError("Invalid workspace path")

        bits, _ = self.container.get_archive(f"/workspace/{safe_path}")
        tf = tarfile.open(fileobj=io.BytesIO(b"".join(bits)))
        member = tf.getmembers()[0]
        extracted = tf.extractfile(member)
        if extracted is None:
            raise ValueError(f"{safe_path} is not a file")
        return extracted.read().decode("utf-8")

    def download_workspace_zip(self) -> bytes:
        """Download the workspace as a zip archive."""
        bits, _ = self.container.get_archive('/workspace')
        
        tar_buf = io.BytesIO(b"".join(bits))
        zip_buf = io.BytesIO()
        
        with tarfile.open(fileobj=tar_buf) as tar:
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for member in tar.getmembers():
                    if member.isfile():
                        f = tar.extractfile(member)
                        if f:
                            name = member.name
                            if name.startswith('workspace/'):
                                name = name[len('workspace/'):]
                            if name:
                                zipf.writestr(name, f.read())
                                
        return zip_buf.getvalue()

    # ── Lifecycle (from OpenHands) ──────────────────────────────────────

    def pause(self) -> bool:
        """Pause the container (preserves state, frees CPU)."""
        try:
            self.container.reload()
            if self.container.status == 'running':
                if hasattr(self, 'shell') and self.shell.isalive():
                    self.shell.close()
                self.container.pause()
                logger.info("container_paused", session_id=self.session_id)
                return True
        except Exception as e:
            logger.error("container_pause_error", session_id=self.session_id, error=str(e))
        return False

    def resume(self) -> bool:
        """Resume a paused container."""
        try:
            self.container.reload()
            if self.container.status == 'paused':
                self.container.unpause()
                self._init_shell()
                logger.info("container_resumed", session_id=self.session_id)
                return True
            elif self.container.status == 'exited':
                self.container.start()
                self._init_shell()
                logger.info("container_restarted", session_id=self.session_id)
                return True
        except Exception as e:
            logger.error("container_resume_error", session_id=self.session_id, error=str(e))
        return False

    # ── Action execution ────────────────────────────────────────────────

    async def execute(self, action: ActionType) -> dict:
        if isinstance(action, CmdRunAction):
            loop = asyncio.get_event_loop()

            def run_sync():
                try:
                    while True:
                        try:
                            self.shell.read_nonblocking(size=1024, timeout=0.1)
                        except (pexpect.TIMEOUT, pexpect.EOF):
                            break

                    self.shell.sendline(action.command)
                    self.shell.expect(
                        '\\[PROMPT_END\\]# ',
                        timeout=settings.SANDBOX_TIMEOUT,
                    )

                    raw_output = self.shell.before
                    lines = raw_output.split('\n')
                    if len(lines) > 0 and action.command.strip() in lines[0]:
                        output = '\n'.join(lines[1:]).strip()
                    else:
                        output = raw_output.strip()

                    self.shell.sendline('echo $?')
                    self.shell.expect('\\[PROMPT_END\\]# ', timeout=5)
                    
                    ansi_escape = re_mod.compile(r'(?:\x1B[@-Z\\-_]|\x1B\[[0-?]*[ -/]*[@-~])')
                    cleaned_before = ansi_escape.sub('', self.shell.before)
                    exit_code_str = cleaned_before.strip().split('\n')[-1].strip()
                    try:
                        exit_code = int(exit_code_str)
                    except ValueError:
                        exit_code = 1

                    cleaned_output = ansi_escape.sub('', output).strip()
                    return {'output': cleaned_output, 'exit_code': exit_code}

                except pexpect.TIMEOUT:
                    self.shell.sendcontrol('c')
                    try:
                        self.shell.expect('\\[PROMPT_END\\]# ', timeout=5)
                    except pexpect.TIMEOUT:
                        pass
                    return {
                        'output': f'Command timed out after {settings.SANDBOX_TIMEOUT}s (SIGINT sent).',
                        'exit_code': 124,
                    }
                except Exception as e:
                    return {'output': f'Error: {str(e)}', 'exit_code': 1}

            return await loop.run_in_executor(None, run_sync)

        elif isinstance(action, BrowserAction):
            browser = await PlaywrightManager.get_instance()
            target = action.target
            # Replace localhost with host-mapped port (more reliable than container IP)
            if 'localhost' in target or '127.0.0.1' in target:
                port_match = re_mod.search(r':(\d+)', target)
                if port_match:
                    container_port = int(port_match.group(1))
                    for ep in self.exposed_ports:
                        if ep.container_port == container_port:
                            target = re_mod.sub(
                                r'(localhost|127\.0\.0\.1):\d+',
                                f'localhost:{ep.host_port}',
                                target,
                            )
                            break
                else:
                    target = (
                        target
                        .replace('localhost', self.container_ip)
                        .replace('127.0.0.1', self.container_ip)
                    )
            return await browser.execute_action(action.command, target)

        elif isinstance(action, FileWriteAction):
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode='w') as tar:
                data = action.content.encode('utf-8')
                info = tarfile.TarInfo(name=action.path)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            buf.seek(0)
            self.container.put_archive('/workspace', buf)
            return {'status': 'written', 'path': action.path, 'exit_code': 0, 'output': f"Created {action.path}"}

        elif isinstance(action, FileReadAction):
            try:
                content = self.read_file(action.path)
                return {'content': content, 'exit_code': 0, 'output': f"Read {action.path}"}
            except Exception as e:
                return {'error': str(e), 'exit_code': 1, 'output': f"Failed to read {action.path}: {str(e)}"}

        return {'output': 'Unsupported action', 'exit_code': 1}

    # ── Cleanup ─────────────────────────────────────────────────────────

    def cleanup(self):
        """Stop and remove the container."""
        logger.info("container_cleanup", session_id=self.session_id)
        try:
            if hasattr(self, 'shell') and self.shell.isalive():
                self.shell.close()
            self.container.stop(timeout=10)
            try:
                self.container.remove()
            except Exception:
                pass
        except Exception as e:
            logger.error("container_cleanup_error", session_id=self.session_id, error=str(e))

        self._local_cache.pop(self.session_id, None)
        try:
            r = _get_redis()
            r.delete(f"{self.REDIS_KEY_PREFIX}{self.session_id}")
        except Exception:
            pass
