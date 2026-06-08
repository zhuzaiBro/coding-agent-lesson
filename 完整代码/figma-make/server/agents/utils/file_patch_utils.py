"""Shared helpers for LLM file patch nodes (debug fix / user modify)."""
import re
from typing import Dict, List, Optional, Set


def normalize_sandpack_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def paths_from_build_log(error: str) -> Set[str]:
    found: Set[str] = set()
    for match in re.finditer(
        r"(?:[/\\]?[\w.-]+)+[/\\][\w.-]+\.(?:tsx?|jsx?|css)",
        error,
    ):
        raw = match.group(0).replace("\\", "/")
        if raw.startswith("src/"):
            found.add(normalize_sandpack_path(raw[len("src/") :]))
        elif raw.startswith("/src/"):
            found.add(normalize_sandpack_path(raw[len("/src/") :]))
        else:
            found.add(normalize_sandpack_path(raw.lstrip("/")))
    return found


def paths_from_user_text(text: str) -> Set[str]:
    found: Set[str] = set()
    for match in re.finditer(
        r"(?:@/)?(?:src/)?([\w.-]+(?:/[\w.-]+)*\.(?:tsx?|jsx?|css))",
        text,
        re.IGNORECASE,
    ):
        found.add(normalize_sandpack_path(match.group(1)))
    for token in ("App.tsx", "index.tsx", "styles.css", "package.json"):
        if token.lower() in text.lower():
            found.add(normalize_sandpack_path(token))
    return found


def resolve_patch_path(path: str, file_map: Dict[str, str]) -> Optional[str]:
    normalized = normalize_sandpack_path(path)
    if normalized in file_map:
        return normalized
    if normalized.startswith("/src/"):
        root = normalize_sandpack_path(normalized[len("/src/") :])
        if root in file_map:
            return root
    src_path = f"/src{normalized}"
    if src_path in file_map:
        return src_path
    return None


def select_context_files(
    file_map: Dict[str, str],
    *,
    priority_paths: Optional[Set[str]] = None,
    max_files: int = 16,
    max_chars_per_file: int = 12000,
) -> Dict[str, str]:
    priority_paths = priority_paths or set()
    ordered: List[str] = []

    for path in sorted(priority_paths):
        if path in file_map and path not in ordered:
            ordered.append(path)

    for path in ["/package.json", "/App.tsx", "/index.tsx", "/styles.css"]:
        if path in file_map and path not in ordered:
            ordered.append(path)

    for path in sorted(file_map):
        if path.endswith((".ts", ".tsx", ".js", ".jsx", ".css")) and path not in ordered:
            ordered.append(path)
        if len(ordered) >= max_files:
            break

    selected: Dict[str, str] = {}
    for path in ordered[:max_files]:
        content = file_map[path]
        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file] + "\n/* ... truncated ... */\n"
        selected[path] = content
    return selected
