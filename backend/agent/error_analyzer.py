"""
Error Intelligence — classification, analysis, and self-healing.

Architecture (from AUTONOMOUS_AI_AGENT_ARCHITECTURE.md §9):
  - Error detection: compile, runtime, test failures
  - Error classification: syntax, type, import, runtime, dependency, etc.
  - Stack trace parsing: extract file, line, error type from Python/Node.js output
  - LLM-based analysis: generate targeted fix suggestions
  - Self-healing: auto-remediation strategies per error type
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)


# ── Error categories ───────────────────────────────────────────────────

class ErrorCategory(str, Enum):
    SYNTAX = "syntax"
    TYPE = "type"
    IMPORT = "import"
    RUNTIME = "runtime"
    DEPENDENCY = "dependency"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    NETWORK = "network"
    FILE_NOT_FOUND = "file_not_found"
    PORT_IN_USE = "port_in_use"
    BUILD = "build"
    TEST = "test"
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    LOW = "low"          # Warnings, non-blocking
    MEDIUM = "medium"    # Errors that can likely be fixed automatically
    HIGH = "high"        # Critical errors needing significant changes
    FATAL = "fatal"      # Unrecoverable without major intervention


# ── Stack trace parsing ────────────────────────────────────────────────

@dataclass
class StackFrame:
    """A single frame from a stack trace."""
    file: str
    line: Optional[int] = None
    function: Optional[str] = None
    code: Optional[str] = None


@dataclass
class ParsedError:
    """Structured representation of an error."""
    category: ErrorCategory
    severity: ErrorSeverity
    error_type: str          # e.g., "SyntaxError", "ENOENT"
    message: str             # The error message text
    file: Optional[str] = None
    line: Optional[int] = None
    stack_frames: List[StackFrame] = field(default_factory=list)
    raw_output: str = ""
    suggestion: str = ""     # Auto-generated fix suggestion


# ── Classification patterns ────────────────────────────────────────────

_CLASSIFICATION_RULES: List[tuple[ErrorCategory, ErrorSeverity, list[str]]] = [
    # (category, severity, patterns)
    (ErrorCategory.SYNTAX, ErrorSeverity.MEDIUM, [
        r"SyntaxError",
        r"Unexpected token",
        r"Unexpected end of",
        r"Parsing error",
        r"Expected .*? but found",
        r"Unterminated string",
        r"Invalid syntax",
        r"unexpected EOF",
    ]),
    (ErrorCategory.TYPE, ErrorSeverity.MEDIUM, [
        r"TypeError",
        r"Type '.*?' is not assignable",
        r"Property '.*?' does not exist",
        r"Cannot read propert(?:y|ies) of (?:undefined|null)",
        r"is not a function",
        r"is not iterable",
    ]),
    (ErrorCategory.IMPORT, ErrorSeverity.MEDIUM, [
        r"ModuleNotFoundError",
        r"ImportError",
        r"Cannot find module",
        r"Module not found",
        r"No module named",
        r"Could not resolve",
        r"Module '.*?' has no (?:default )?export",
    ]),
    (ErrorCategory.DEPENDENCY, ErrorSeverity.HIGH, [
        r"npm ERR!",
        r"ERESOLVE",
        r"peer dep",
        r"Could not resolve dependency",
        r"No matching version found",
        r"pip.*?error",
        r"PackageNotFoundError",
        r"ENOTEMPTY",
    ]),
    (ErrorCategory.FILE_NOT_FOUND, ErrorSeverity.MEDIUM, [
        r"ENOENT",
        r"FileNotFoundError",
        r"No such file or directory",
        r"EISDIR",
        r"path.*?does not exist",
    ]),
    (ErrorCategory.PERMISSION, ErrorSeverity.HIGH, [
        r"EACCES",
        r"Permission denied",
        r"PermissionError",
        r"EPERM",
    ]),
    (ErrorCategory.PORT_IN_USE, ErrorSeverity.MEDIUM, [
        r"EADDRINUSE",
        r"address already in use",
        r"port.*?already in use",
        r"listen EADDRINUSE",
    ]),
    (ErrorCategory.TIMEOUT, ErrorSeverity.LOW, [
        r"timed? ?out",
        r"ETIMEDOUT",
        r"ESOCKETTIMEDOUT",
        r"TimeoutError",
    ]),
    (ErrorCategory.NETWORK, ErrorSeverity.LOW, [
        r"ECONNREFUSED",
        r"ENOTFOUND",
        r"fetch failed",
        r"ConnectionRefusedError",
        r"ConnectionError",
    ]),
    (ErrorCategory.BUILD, ErrorSeverity.HIGH, [
        r"Build failed",
        r"Compilation failed",
        r"tsc.*?error",
        r"webpack.*?error",
        r"vite.*?error",
        r"esbuild.*?error",
    ]),
    (ErrorCategory.TEST, ErrorSeverity.MEDIUM, [
        r"FAIL",
        r"AssertionError",
        r"test.*?failed",
        r"expect\(.*?\)\.to",
    ]),
]


# ── Stack trace parsers ────────────────────────────────────────────────

def _parse_python_traceback(output: str) -> List[StackFrame]:
    """Parse Python traceback format."""
    frames = []
    # Pattern: File "path", line N, in function
    for match in re.finditer(
        r'File "([^"]+)", line (\d+)(?:, in (.+))?', output
    ):
        frames.append(StackFrame(
            file=match.group(1),
            line=int(match.group(2)),
            function=match.group(3),
        ))
    return frames


def _parse_node_stacktrace(output: str) -> List[StackFrame]:
    """Parse Node.js/JavaScript stack trace format."""
    frames = []
    # Pattern: at FunctionName (path:line:col)
    for match in re.finditer(
        r'at\s+(?:(.+?)\s+)?\(?((?:/|[A-Z]:)[^:]+):(\d+)(?::\d+)?\)?', output
    ):
        frames.append(StackFrame(
            file=match.group(2),
            line=int(match.group(3)),
            function=match.group(1),
        ))
    # Also match: path:line:col
    for match in re.finditer(
        r'^((?:/|\.)[^\s:]+):(\d+)(?::\d+)?', output, re.MULTILINE
    ):
        if not any(f.file == match.group(1) and f.line == int(match.group(2)) for f in frames):
            frames.append(StackFrame(
                file=match.group(1),
                line=int(match.group(2)),
            ))
    return frames


def _parse_generic_stacktrace(output: str) -> List[StackFrame]:
    """Fallback parser for other stack trace formats."""
    frames = []
    for match in re.finditer(r'([^\s:]+\.[a-z]{1,4}):(\d+)', output):
        frames.append(StackFrame(
            file=match.group(1),
            line=int(match.group(2)),
        ))
    return frames


# ── Self-healing suggestions ───────────────────────────────────────────

_HEALING_STRATEGIES: Dict[ErrorCategory, str] = {
    ErrorCategory.DEPENDENCY: (
        "Run dependency installation:\n"
        "- For Node.js: `npm install` or `npm install <missing-package>`\n"
        "- For Python: `pip install <missing-package>`"
    ),
    ErrorCategory.IMPORT: (
        "The import path is wrong or the module isn't installed:\n"
        "1. Check if the module is listed in package.json/requirements.txt\n"
        "2. Verify the import path matches the actual file location\n"
        "3. If it's a relative import, check ../ paths"
    ),
    ErrorCategory.SYNTAX: (
        "Syntax error in the code:\n"
        "1. Check the specific file and line number\n"
        "2. Look for missing brackets, commas, or semicolons\n"
        "3. Re-generate the file with correct syntax"
    ),
    ErrorCategory.TYPE: (
        "Type mismatch or undefined property:\n"
        "1. Check if the variable/property exists\n"
        "2. Add null/undefined checks\n"
        "3. Verify the expected interface/type"
    ),
    ErrorCategory.FILE_NOT_FOUND: (
        "A required file doesn't exist:\n"
        "1. Create the missing file\n"
        "2. Check if the path is correct (case-sensitive on Linux)\n"
        "3. Verify working directory"
    ),
    ErrorCategory.PORT_IN_USE: (
        "Port is already in use:\n"
        "1. Kill the existing process: `lsof -ti:PORT | xargs kill -9`\n"
        "2. Or use a different port"
    ),
    ErrorCategory.PERMISSION: (
        "Permission denied:\n"
        "1. Check file/directory permissions with `ls -la`\n"
        "2. Use `chmod` to fix permissions\n"
        "3. Ensure the user has write access"
    ),
    ErrorCategory.TIMEOUT: (
        "Operation timed out:\n"
        "1. The server might not be ready yet — wait and retry\n"
        "2. Check if the service is running\n"
        "3. Increase timeout if needed"
    ),
    ErrorCategory.NETWORK: (
        "Network connection failed:\n"
        "1. Check if the target service is running\n"
        "2. Verify the URL/host/port\n"
        "3. Check for firewall or DNS issues"
    ),
    ErrorCategory.BUILD: (
        "Build failed:\n"
        "1. Check the specific error in build output\n"
        "2. Ensure all dependencies are installed\n"
        "3. Verify TypeScript/config settings"
    ),
}


# ── Main API ───────────────────────────────────────────────────────────

class ErrorAnalyzer:
    """
    Analyzes errors from command execution and provides structured insights.

    Usage:
        analyzer = ErrorAnalyzer()
        parsed = analyzer.analyze("npm ERR! Cannot find module 'express'")
        print(parsed.category)     # ErrorCategory.DEPENDENCY
        print(parsed.suggestion)   # "Run npm install express"
    """

    def analyze(self, output: str, exit_code: int = 1) -> ParsedError:
        """
        Analyze error output and return structured error information.

        Args:
            output: The stderr/stdout from the failed command
            exit_code: The process exit code

        Returns:
            ParsedError with classification, stack trace, and fix suggestion
        """
        if not output or exit_code == 0:
            return ParsedError(
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.LOW,
                error_type="none",
                message="No error detected",
                raw_output=output or "",
            )

        # 1. Classify the error
        category, severity = self._classify(output)

        # 2. Extract error type and message
        error_type, message = self._extract_error_message(output)

        # 3. Parse stack trace
        stack_frames = self._parse_stack(output)

        # 4. Extract file and line from stack or error message
        file_path = None
        line_num = None
        if stack_frames:
            # Use the most relevant frame (usually the first non-internal one)
            for frame in stack_frames:
                if frame.file and not any(
                    skip in frame.file
                    for skip in ["node_modules", "internal/", "<frozen", "__pycache__"]
                ):
                    file_path = frame.file
                    line_num = frame.line
                    break
            if not file_path and stack_frames:
                file_path = stack_frames[0].file
                line_num = stack_frames[0].line

        # 5. Generate fix suggestion
        suggestion = self._generate_suggestion(category, output, error_type, message)

        parsed = ParsedError(
            category=category,
            severity=severity,
            error_type=error_type,
            message=message,
            file=file_path,
            line=line_num,
            stack_frames=stack_frames,
            raw_output=output,
            suggestion=suggestion,
        )

        logger.info(
            "error_analyzed",
            category=category.value,
            severity=severity.value,
            error_type=error_type,
            file=file_path,
            line=line_num,
        )

        return parsed

    def _classify(self, output: str) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by matching against known patterns."""
        for category, severity, patterns in _CLASSIFICATION_RULES:
            for pattern in patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    return category, severity
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM

    def _extract_error_message(self, output: str) -> tuple[str, str]:
        """Extract the error type and human-readable message."""
        # Python errors: "ErrorType: message"
        match = re.search(
            r"((?:[A-Z][a-zA-Z]*Error|Exception|Warning))\s*:\s*(.+?)$",
            output,
            re.MULTILINE,
        )
        if match:
            return match.group(1), match.group(2).strip()

        # Node.js/npm errors: "Error: message"
        match = re.search(r"Error:\s*(.+?)$", output, re.MULTILINE)
        if match:
            return "Error", match.group(1).strip()

        # npm ERR!
        match = re.search(r"npm ERR!\s*(.+?)$", output, re.MULTILINE)
        if match:
            return "npm_error", match.group(1).strip()

        # TypeScript errors: "error TS####: message"
        match = re.search(r"error (TS\d+):\s*(.+?)$", output, re.MULTILINE)
        if match:
            return match.group(1), match.group(2).strip()

        # Generic: first non-empty line with "error" in it
        for line in output.split("\n"):
            if "error" in line.lower() and len(line.strip()) > 5:
                return "Error", line.strip()[:200]

        # Fallback
        first_line = output.strip().split("\n")[0][:200]
        return "Unknown", first_line

    def _parse_stack(self, output: str) -> List[StackFrame]:
        """Parse stack trace from output (auto-detects Python vs Node.js)."""
        # Try Python first
        if "Traceback" in output or 'File "' in output:
            frames = _parse_python_traceback(output)
            if frames:
                return frames

        # Try Node.js
        if "    at " in output:
            frames = _parse_node_stacktrace(output)
            if frames:
                return frames

        # Generic fallback
        return _parse_generic_stacktrace(output)

    def _generate_suggestion(
        self,
        category: ErrorCategory,
        output: str,
        error_type: str,
        message: str,
    ) -> str:
        """Generate a targeted fix suggestion based on error analysis."""
        parts = []

        # Base strategy from category
        base = _HEALING_STRATEGIES.get(category, "")
        if base:
            parts.append(base)

        # Category-specific enrichment
        if category == ErrorCategory.IMPORT:
            # Try to extract the missing module name
            mod_match = re.search(
                r"(?:No module named|Cannot find module|Module not found)\s*['\"]([^'\"]+)['\"]",
                output,
            )
            if mod_match:
                module = mod_match.group(1)
                parts.append(f"\nMissing module: `{module}`")
                parts.append(f"Try: `npm install {module}` or `pip install {module}`")

        elif category == ErrorCategory.DEPENDENCY:
            pkg_match = re.search(r"npm ERR!\s.*?([a-z@][a-z0-9@/_.-]+)", output)
            if pkg_match:
                parts.append(f"\nProblem package: `{pkg_match.group(1)}`")

        elif category == ErrorCategory.SYNTAX:
            # Extract line info
            line_match = re.search(r"line (\d+)", output, re.IGNORECASE)
            if line_match:
                parts.append(f"\nError at line {line_match.group(1)} — re-check that section")

        elif category == ErrorCategory.PORT_IN_USE:
            port_match = re.search(r"(?:port|EADDRINUSE.*?:)\s*(\d+)", output, re.IGNORECASE)
            if port_match:
                port = port_match.group(1)
                parts.append(f"\nPort {port} is busy. Kill it: `lsof -ti:{port} | xargs kill -9`")

        return "\n".join(parts) if parts else f"Error type: {error_type}. Review the output and fix."

    def format_for_prompt(self, parsed: ParsedError) -> str:
        """
        Format the error analysis as context for the LLM prompt.
        This gives the agent much better information than raw stderr.
        """
        parts = [
            f"ERROR ANALYSIS:",
            f"  Category: {parsed.category.value}",
            f"  Severity: {parsed.severity.value}",
            f"  Type: {parsed.error_type}",
            f"  Message: {parsed.message}",
        ]

        if parsed.file:
            loc = f"  Location: {parsed.file}"
            if parsed.line:
                loc += f":{parsed.line}"
            parts.append(loc)

        if parsed.suggestion:
            parts.append(f"  Suggested Fix: {parsed.suggestion}")

        # Include relevant raw output (truncated)
        raw = parsed.raw_output
        if len(raw) > 500:
            raw = raw[:500] + "\n...[truncated]"
        parts.append(f"\n  Raw Output:\n{raw}")

        return "\n".join(parts)

    def should_retry(self, parsed: ParsedError, current_retries: int) -> bool:
        """
        Decide whether to retry based on error analysis.
        
        Some errors are worth retrying (syntax, type) because the LLM
        can fix them. Others (permission, network) probably won't change.
        """
        if parsed.severity == ErrorSeverity.FATAL:
            return False

        # These error types can usually be fixed by the agent
        fixable = {
            ErrorCategory.SYNTAX,
            ErrorCategory.TYPE,
            ErrorCategory.IMPORT,
            ErrorCategory.FILE_NOT_FOUND,
            ErrorCategory.PORT_IN_USE,
            ErrorCategory.DEPENDENCY,
            ErrorCategory.BUILD,
        }

        if parsed.category in fixable:
            return current_retries < 5

        # Non-fixable errors get fewer retries
        return current_retries < 2
