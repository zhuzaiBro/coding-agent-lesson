"""
JSX/TSX parser utility (regex-based).

Python equivalent of the TypeScript Babel-based parser.
Uses regex to extract:
1. Main entry component (export default)
2. Top-level JSX elements in the main component's return block
3. Global image asset variables (const imgXxx = "https://...")
4. Helper components (non-default-export function components)
"""
import re
from typing import Any, Dict, List, Optional, Tuple


def _extract_global_assets(code: str) -> List[Dict[str, str]]:
    """Extract global image asset variable declarations."""
    assets = []
    pattern = r"""(?:export\s+)?const\s+(img[A-Za-z0-9]\w*)\s*=\s*["']([^"']+)["']\s*;?"""
    for m in re.finditer(pattern, code):
        var_name, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://")):
            assets.append({"variableName": var_name, "url": url})
    return assets


def _find_default_export_name(code: str) -> Optional[str]:
    """Find the name of the default exported component."""
    # export default function ComponentName
    m = re.search(r"export\s+default\s+function\s+(\w+)", code)
    if m:
        return m.group(1)

    # export default ComponentName (identifier)
    m = re.search(r"export\s+default\s+(\w+)\s*;", code)
    if m:
        name = m.group(1)
        if name not in ("class", "function", "const", "let", "var"):
            return name

    return None


def _find_matching_brace(code: str, start: int) -> int:
    """Find the matching closing brace for the opening brace at start."""
    depth = 0
    i = start
    while i < len(code):
        c = code[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _find_component_body(code: str, component_name: str) -> Optional[str]:
    """Extract the body of a named component function."""
    # Try function declaration: function Name(...) {
    pattern = rf"function\s+{re.escape(component_name)}\s*\([^)]*\)\s*\{{"
    m = re.search(pattern, code)
    if m:
        brace_start = m.end() - 1
        brace_end = _find_matching_brace(code, brace_start)
        if brace_end > 0:
            return code[brace_start:brace_end + 1]

    # Try arrow function: const Name = (...) => {
    pattern = rf"const\s+{re.escape(component_name)}\s*=\s*(?:\([^)]*\)|\w+)\s*=>\s*\{{"
    m = re.search(pattern, code)
    if m:
        brace_start = m.end() - 1
        brace_end = _find_matching_brace(code, brace_start)
        if brace_end > 0:
            return code[brace_start:brace_end + 1]

    return None


def _extract_top_level_jsx_elements(return_block: str, lines: List[str], code_offset: int) -> List[Dict[str, Any]]:
    """
    Extract top-level JSX elements from a return block.
    Uses regex to find direct children of the return statement.
    """
    elements = []

    # Find the return ( ... ) block
    return_match = re.search(r"\breturn\s*\(", return_block)
    if not return_match:
        # Try return without parens
        return_match = re.search(r"\breturn\s+<", return_block)
        if not return_match:
            return elements

    # Simple heuristic: find all top-level JSX opening tags
    # We look for elements that start with < at the first level of nesting inside return(...)
    return_start = return_match.start()
    remaining = return_block[return_start:]

    # Find top-level JSX elements using a depth-based approach
    depth = 0
    i = 0
    in_return_parens = False
    elements_raw = []

    # Scan for JSX element boundaries
    jsx_pattern = re.compile(r"<([A-Za-z][A-Za-z0-9]*|[a-z]+)[\s>]")

    # Simple extraction: find blocks that look like complete JSX elements
    # between { } or as direct children
    block_pattern = re.compile(r"\{(/\*.*?\*/|[^{}]*)\}", re.DOTALL)

    # Use a simpler approach: find all child elements by looking at direct JSX children
    child_pattern = re.compile(
        r"(<(?:[A-Za-z][A-Za-z0-9.]*|[a-z]+)(?:\s[^>]*)?>(?:[\s\S]*?)</[A-Za-z][A-Za-z0-9.]*>|"
        r"<(?:[A-Za-z][A-Za-z0-9.]*|[a-z]+)(?:\s[^>]*)?\s*/>)"
    )

    # For each match, record it as a JSX element
    idx = 0
    for m in re.finditer(
        r"(<(?:div|section|header|footer|nav|main|article|aside|span|p|h[1-6]|img|button|a|ul|ol|li|form|input|[A-Z][A-Za-z0-9]*)"
        r"[\s\S]*?(?:</[A-Za-z][A-Za-z0-9]*>|/>))",
        return_block,
    ):
        raw_jsx = m.group(0)
        # Skip very short snippets (closing tags, etc.)
        if len(raw_jsx) < 5:
            continue

        # Estimate source location
        start_pos = m.start()
        before = return_block[:start_pos]
        start_line = before.count("\n") + 1

        # Extract class name
        class_m = re.search(r'className=["\']([^"\']*)["\']', raw_jsx)
        class_name = class_m.group(1) if class_m else None

        # Extract inline style
        style_m = re.search(r'style=\{(\{[^}]*\})\}', raw_jsx)
        inline_style = style_m.group(1) if style_m else None

        # Extract data-node-id
        node_id_m = re.search(r'data-node-id=["\']([^"\']*)["\']', raw_jsx)
        node_id = node_id_m.group(1) if node_id_m else None

        # Extract data-name
        data_name_m = re.search(r'data-name=["\']([^"\']*)["\']', raw_jsx)
        data_name = data_name_m.group(1) if data_name_m else None

        # Count children (simple heuristic)
        children_count = len(re.findall(r"<[A-Za-z][A-Za-z0-9]*[\s>]", raw_jsx)) - 1

        elements.append({
            "index": idx,
            "rawJsx": raw_jsx,
            "className": class_name,
            "inlineStyle": inline_style,
            "nodeId": node_id,
            "dataName": data_name,
            "childrenCount": max(0, children_count),
            "loc": {"startLine": start_line, "endLine": start_line + raw_jsx.count("\n")},
        })
        idx += 1

        # Only take top-level elements (first 30 max)
        if idx >= 30:
            break

    return elements


def _extract_helper_components(code: str, entry_name: str) -> List[Dict[str, Any]]:
    """Extract helper components (non-default-export function components)."""
    helpers = []
    lines = code.split("\n")

    # Function declarations: function ComponentName(...)
    for m in re.finditer(r"(?:^|\n)(function\s+([A-Z]\w*)\s*\([^)]*\)\s*\{)", code):
        name = m.group(2)
        if name == entry_name:
            continue

        start_pos = m.start(1) if m.start(1) > 0 else m.start()
        brace_pos = code.index("{", start_pos + m.start(1) - m.start())
        end_pos = _find_matching_brace(code, code.index("{", start_pos))
        if end_pos < 0:
            continue

        raw_code = code[start_pos:end_pos + 1]

        # Check if it looks like a React component (returns JSX)
        if "<" not in raw_code:
            continue

        start_line = code[:start_pos].count("\n") + 1
        end_line = code[:end_pos].count("\n") + 1

        helpers.append({
            "name": name,
            "rawCode": raw_code,
            "loc": {"startLine": start_line, "endLine": end_line},
        })

    return helpers


def parse_tsx_code(raw_code: str) -> Dict[str, Any]:
    """
    Parse TSX source code and extract structural information.

    Returns AstParserOutput compatible dict:
    {
        entryComponentName: str,
        jsxElements: List[JsxElement],
        globalAssets: List[GlobalAsset],
        helperComponents: List[HelperComponent],
    }
    """
    lines = raw_code.split("\n")

    # 1. Find default export name
    entry_name = _find_default_export_name(raw_code) or "App"

    # 2. Extract global image assets
    global_assets = _extract_global_assets(raw_code)

    # 3. Extract helper components
    helper_components = _extract_helper_components(raw_code, entry_name)

    # 4. Extract top-level JSX elements from main component
    component_body = _find_component_body(raw_code, entry_name)
    jsx_elements = []
    if component_body:
        jsx_elements = _extract_top_level_jsx_elements(component_body, lines, 0)

    # If no elements found from body, try simpler approach
    if not jsx_elements:
        # Look for common top-level divs with absolute positioning (Figma pattern)
        for i, m in enumerate(re.finditer(
            r'(<(?:div|section)\s+[^>]*className=["\'][^"\']*(?:absolute|relative)[^"\']*["\'][^>]*>[\s\S]{10,}?(?:</div>|/>))',
            raw_code[:5000],  # Only scan first 5000 chars for performance
        )):
            if i >= 20:
                break
            raw_jsx = m.group(1)
            class_m = re.search(r'className=["\']([^"\']*)["\']', raw_jsx)
            jsx_elements.append({
                "index": i,
                "rawJsx": raw_jsx,
                "className": class_m.group(1) if class_m else None,
                "inlineStyle": None,
                "nodeId": None,
                "dataName": None,
                "childrenCount": 0,
                "loc": {"startLine": 1, "endLine": 1},
            })

    return {
        "entryComponentName": entry_name,
        "jsxElements": jsx_elements,
        "globalAssets": global_assets,
        "helperComponents": helper_components,
    }
