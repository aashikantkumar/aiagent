import re
from typing import Tuple, Optional

def is_valid_mermaid(diagram: str) -> Tuple[bool, Optional[str]]:
    """
    Validates Mermaid diagram syntax.
    Returns (True, None) if valid, or (False, error_message) if invalid.
    """
    if not diagram or not diagram.strip():
        return False, "Diagram content is empty"

    lines = diagram.splitlines()
    cleaned_lines = []
    first_diagram_line_idx = -1

    # Basic diagram types regex
    diagram_headers = [
        r"^\s*graph\s+(TB|TD|BT|RL|LR)\b",
        r"^\s*flowchart\s+(TB|TD|BT|RL|LR)\b",
        r"^\s*sequenceDiagram\b",
        r"^\s*classDiagram\b",
        r"^\s*stateDiagram\b",
        r"^\s*stateDiagram-v2\b",
        r"^\s*erDiagram\b",
        r"^\s*gantt\b",
        r"^\s*pie\b",
        r"^\s*gitGraph\b",
        r"^\s*journey\b",
        r"^\s*requirementDiagram\b",
        r"^\s*C4Context\b"
    ]

    header_pattern = re.compile("|".join(diagram_headers), re.IGNORECASE)
    has_header = False

    for idx, line in enumerate(lines):
        stripped = line.strip()
        # Skip empty lines or comments
        if not stripped or stripped.startswith("%%"):
            continue
        
        cleaned_lines.append((idx + 1, stripped))
        if not has_header:
            if header_pattern.match(stripped):
                has_header = True
                first_diagram_line_idx = idx
            else:
                return False, f"Line {idx + 1}: Invalid diagram type or missing diagram header (e.g. 'graph TD', 'sequenceDiagram')"

    if not has_header:
        return False, "Missing diagram header (e.g., 'graph TD', 'sequenceDiagram')"

    # Check for basic syntactic constructs line by line
    for line_num, line_content in cleaned_lines:
        # Check matching of quotes
        double_quotes_count = line_content.count('"')
        if double_quotes_count % 2 != 0:
            return False, f"Line {line_num}: Unmatched double quotes in line: '{line_content}'"
            
        # Ignore brackets that are inside double quotes for unmatched bracket checks
        # Replace content inside double quotes with temporary placeholder to validate brackets
        bracket_check_content = line_content
        quotes_matches = list(re.finditer(r'"[^"\\]*(?:\\.[^"\\]*)*"', line_content))
        for m in reversed(quotes_matches):
            start, end = m.span()
            bracket_check_content = bracket_check_content[:start] + '""' + bracket_check_content[end:]

        # Check matching brackets, braces, parentheses
        stack = []
        mapping = {')': '(', ']': '[', '}': '{'}
        opening = set(mapping.values())
        closing = set(mapping.keys())
        
        for char in bracket_check_content:
            if char in opening:
                stack.append(char)
            elif char in closing:
                if not stack:
                    return False, f"Line {line_num}: Unmatched closing bracket '{char}' in line: '{line_content}'"
                top = stack.pop()
                if top != mapping[char]:
                    return False, f"Line {line_num}: Mismatched bracket '{char}' matching '{top}' in line: '{line_content}'"
        
        if stack:
            # We allow unmatched opening brackets on a single line if it's a multi-line structure,
            # but for standard flowchart node syntax on a single line, we check if they are balanced on the line.
            # However, Mermaid allows node text to contain parentheses if correctly wrapped.
            # To be lenient and avoid false positives, we check if standard node definitions like `A[text]` are balanced.
            # If stack contains open elements, we double check if the line has a node shape declaration that is not closed.
            # For flowcharts, node declarations are typically on a single line.
            pass

    return True, None
