"""Build concrete file/import context blocks for LLM human messages."""
import re
from pathlib import PurePosixPath
from typing import List, Optional, Set

from agents.utils.export_repair import HAS_DEFAULT_EXPORT_RE, parse_named_exports


def _basename(path: str) -> str:
    name = (path or "").rsplit("/", 1)[-1]
    for suffix in (".tsx", ".ts", ".jsx", ".js"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _file_code(item: dict) -> str:
    return (item.get("content") or item.get("code") or "") if isinstance(item, dict) else ""


def _default_export_symbol(content: str, path: str) -> Optional[str]:
    code = content or ""
    for pattern in (
        r"""export\s+default\s+function\s+(\w+)""",
        r"""export\s+default\s+class\s+(\w+)""",
        r"""export\s+default\s+(\w+)\s*;?""",
    ):
        match = re.search(pattern, code)
        if match:
            return match.group(1)
    if HAS_DEFAULT_EXPORT_RE.search(code):
        return _basename(path)
    return None


def format_path_list(files: List[dict], *, label: str) -> str:
    paths = [f.get("path") for f in files if isinstance(f, dict) and f.get("path")]
    if not paths:
        return f"{label}: (none — do not invent paths)\n"
    return f"{label}:\n" + "\n".join(f"  - {p}" for p in paths) + "\n"


def format_files_with_exports(
    files: List[dict],
    *,
    label: str,
    path_prefix: Optional[str] = None,
) -> str:
    """File list with parsed named + default exports for strict import constraints."""
    lines: List[str] = [f"{label}:"]
    any_file = False
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or ""
        if path_prefix and not path.startswith(path_prefix):
            continue
        code = _file_code(item)
        named = parse_named_exports(code)
        default_sym = _default_export_symbol(code, path)
        any_file = True
        lines.append(f"  - path: {path}")
        lines.append(f"    namedExports: {named if named else '[]'}")
        lines.append(f"    defaultExport: {default_sym or 'null'}")
        if default_sym:
            lines.append(
                f"    defaultImportExample: import {default_sym} from '<relative-path-without-ext>';"
            )
        if named:
            lines.append(
                f"    namedImportExample: import {{ {', '.join(named[:8])} }} from '<relative-path-without-ext>';"
            )
    if not any_file:
        return f"{label}: (none — do not invent paths or exports)\n"
    return "\n".join(lines) + "\n"


def service_import_manifest(service_files: List[dict]) -> str:
    """How hooks must import each generated service file."""
    lines: List[str] = []
    for item in service_files:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or ""
        if not path.startswith("/services/"):
            continue
        stem = _basename(path)
        lines.append(f"  - {path}  →  import from '../services/{stem}'")
    if not lines:
        return "  (no service files — do not import from ../services/*)\n"
    return "\n".join(lines) + "\n"


def service_export_catalog(service_files: List[dict]) -> str:
    """
    Per-service allowed hook import symbols (parsed from generated code).
    Hooks must ONLY import symbols listed under allowedSymbols.
    """
    lines: List[str] = ["Service export catalog (hooks MUST obey — no other symbols):"]
    any_service = False
    for item in service_files:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or ""
        if not path.startswith("/services/"):
            continue
        stem = _basename(path)
        code = _file_code(item)
        symbols = parse_named_exports(code)
        any_service = True
        lines.append(f"  - servicePath: {path}")
        lines.append(f"    importPath: '../services/{stem}'")
        lines.append(f"    allowedSymbols: {symbols if symbols else '[]'}")
        if symbols:
            lines.append(
                f"    requiredImport: import {{ {', '.join(symbols)} }} from '../services/{stem}';"
            )
        else:
            lines.append(
                "    requiredImport: (service has no named exports yet — call service functions only after they exist in allowedSymbols)"
            )
        file_stem = PurePosixPath(path).stem
        lines.append(
            f"    forbiddenImports: import {{ {file_stem} }}, import {{ {stem} }} as a class/object, default import from service"
        )
    if not any_service:
        return "Service export catalog: (no services — do not import ../services/*)\n"
    return "\n".join(lines) + "\n"


def mock_import_manifest(mock_files: List[dict]) -> str:
    """How services must import each mock data file."""
    lines: List[str] = []
    for item in mock_files:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or ""
        if not path.startswith("/data/"):
            continue
        stem = _basename(path)
        lines.append(f"  - {path}  →  import from '../data/{stem}'")
    if not lines:
        return "  (no mock data files listed)\n"
    return "\n".join(lines) + "\n"


def type_import_manifest(type_files: List[dict]) -> str:
    lines: List[str] = []
    for item in type_files:
        if not isinstance(item, dict):
            continue
        path = item.get("path") or ""
        if not path.startswith("/types/"):
            continue
        stem = _basename(path)
        lines.append(f"  - {path}  →  import from '../types/{stem}'")
    if not lines:
        return "  (no type files listed)\n"
    return "\n".join(lines) + "\n"


def expected_service_paths(mock_files: List[dict]) -> List[str]:
    """Derive required service paths from mock data paths (naming contract)."""
    paths: List[str] = []
    for item in mock_files:
        if not isinstance(item, dict):
            continue
        mock_path = item.get("path") or ""
        if not mock_path.startswith("/data/"):
            continue
        stem = _basename(mock_path)
        if stem.endswith("Data"):
            stem = stem[: -4]
        if not stem:
            continue
        paths.append(f"/services/{stem}Service.ts")
    return paths


def hook_import_manifest(service_files: List[dict], _mock_files: Optional[List[dict]] = None) -> str:
    """Allowed service imports for hook files — only paths that exist in service output."""
    return service_import_manifest(service_files)


def project_files_summary(state_files: List[dict], kinds: Optional[Set[str]] = None) -> str:
    """Compact inventory for downstream generators (pages/components)."""
    kind_map = {
        "/components/": "component",
        "/pages/": "page",
        "/layouts/": "layout",
        "/hooks/": "hook",
        "/services/": "service",
        "/types/": "type",
        "/data/": "data",
    }
    return format_files_with_exports(
        [
            f
            for f in state_files
            if isinstance(f, dict)
            and f.get("path")
            and (kinds is None or any(f["path"].startswith(p) for p in kinds))
        ],
        label="Project file export inventory",
    )
