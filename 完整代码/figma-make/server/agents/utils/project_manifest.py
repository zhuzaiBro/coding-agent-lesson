"""Build a machine-readable project DSL/manifest from pipeline state for downstream LLMs."""
import json
import re
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Set

from agents.utils.export_repair import (
    HAS_DEFAULT_EXPORT_RE,
    HOOK_IMPORT_RE,
    parse_named_exports,
)
from agents.utils.state_helpers import as_dict, as_dict_list, dict_list

DEFAULT_IMPORT_RE = re.compile(
    r"""import\s+(\w+)\s+from\s+['"](\.\./(?:components|layouts|pages|hooks)/[^'"]+)['"]""",
    re.MULTILINE,
)
NAMED_IMPORT_RE = re.compile(
    r"""import\s+\{([^}]+)\}\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)


def _parse_exports(content: str) -> List[str]:
    names: Set[str] = set(parse_named_exports(content or ""))
    if HAS_DEFAULT_EXPORT_RE.search(content or ""):
        names.add("default")
    return sorted(names)


def _parse_default_export_name(content: str, path: str) -> Optional[str]:
    """Best-effort extraction of the default export symbol."""
    code = content or ""
    patterns = [
        r"""export\s+default\s+function\s+(\w+)""",
        r"""export\s+default\s+class\s+(\w+)""",
        r"""export\s+default\s+(\w+)\s*;?""",
    ]
    for pattern in patterns:
        match = re.search(pattern, code)
        if match:
            return match.group(1)

    if HAS_DEFAULT_EXPORT_RE.search(code):
        return PurePosixPath(path).stem
    return None


def _parse_imports(content: str) -> Dict[str, List[str]]:
    imports: Dict[str, List[str]] = {}
    for match in NAMED_IMPORT_RE.finditer(content or ""):
        symbols_raw, spec = match.groups()
        symbols = [s.strip().split(" as ")[0].strip() for s in symbols_raw.split(",") if s.strip()]
        imports.setdefault(spec, []).extend(symbols)
    for match in DEFAULT_IMPORT_RE.finditer(content or ""):
        symbol, spec = match.groups()
        imports.setdefault(spec, []).append(f"default:{symbol}")
    return imports


def _file_kind(path: str) -> str:
    if "/components/" in path:
        return "component"
    if "/pages/" in path:
        return "page"
    if "/layouts/" in path:
        return "layout"
    if "/hooks/" in path:
        return "hook"
    if "/services/" in path:
        return "service"
    if "/types/" in path:
        return "type"
    if "/data/" in path:
        return "data"
    if path.endswith("App.tsx"):
        return "app"
    return "module"


def _normalize_path(path: str) -> str:
    p = (path or "").replace("\\", "/")
    return p if p.startswith("/") else f"/{p}"


def _import_path(from_path: str, target_path: str) -> str:
    """Build extensionless relative import path from one generated file to another."""
    from_dir = PurePosixPath(_normalize_path(from_path)).parent
    target = PurePosixPath(_normalize_path(target_path)).with_suffix("")
    relative = PurePosixPath(
        *(
            [".."] * len(from_dir.parts[1:])
            + list(target.parts[1:])
        )
    )

    try:
        relative = PurePosixPath(
            re.sub(r"^\.\./", "", PurePosixPath(target).relative_to(from_dir).as_posix())
        )
    except ValueError:
        from_parts = list(from_dir.parts[1:])
        target_parts = list(target.parts[1:])
        while from_parts and target_parts and from_parts[0] == target_parts[0]:
            from_parts.pop(0)
            target_parts.pop(0)
        relative = PurePosixPath(*([".."] * len(from_parts) + target_parts))

    spec = relative.as_posix()
    if not spec.startswith("."):
        spec = f"./{spec}"
    return spec


def _allowed_import_forms(
    path: str,
    exports: List[str],
    kind: str,
    default_export: Optional[str],
) -> Dict[str, Any]:
    default_name = default_export or (PurePosixPath(path).stem if "default" in exports else None)
    named_exports = [name for name in exports if name != "default"]

    forms: Dict[str, Any] = {
        "fromApp": _import_path("/App.tsx", path),
    }
    if "default" in exports:
        forms["default"] = {
            "symbol": default_name or PurePosixPath(path).stem,
            "example": f"import {default_name or PurePosixPath(path).stem} from '{forms['fromApp']}';",
        }
    if named_exports:
        forms["named"] = {
            "symbols": named_exports,
            "example": f"import {{ {', '.join(named_exports[:6])} }} from '{forms['fromApp']}';",
        }

    if kind in {"page", "layout", "component"}:
        forms["requiredStyle"] = "default import only unless namedExports explicitly contains the requested symbol"
    else:
        forms["requiredStyle"] = "named imports only unless defaultExport is present"
    return forms


def _collect_files_from_state(state: dict) -> Dict[str, str]:
    """Flatten pipeline state into path -> code."""
    files: Dict[str, str] = {}

    def add(path: Optional[str], code: Optional[str]) -> None:
        if path and code:
            files[_normalize_path(path)] = code

    for item in dict_list(as_dict(state.get("types")), "files"):
        add(item.get("path"), item.get("code") or item.get("content"))
    for item in dict_list(as_dict(state.get("utils")), "files"):
        add(item.get("path"), item.get("code") or item.get("content"))
    for item in dict_list(as_dict(state.get("mockData")), "files"):
        add(item.get("path"), item.get("code") or item.get("content"))
    for item in dict_list(as_dict(state.get("service")), "files"):
        add(item.get("path"), item.get("content") or item.get("code"))
    for item in dict_list(as_dict(state.get("hooks")), "files"):
        add(item.get("path"), item.get("content") or item.get("code"))
    for item in as_dict_list(state.get("componentsCode")):
        add(item.get("path"), item.get("content") or item.get("code"))
    for item in as_dict_list(state.get("pagesCode")):
        add(item.get("path"), item.get("content") or item.get("code"))
    for item in dict_list(as_dict(state.get("layouts")), "layoutsCode"):
        add(item.get("path"), item.get("content") or item.get("code"))

    app = as_dict(state.get("app"))
    add(app.get("path"), app.get("content"))
    styles = as_dict(state.get("styles"))
    add(styles.get("path"), styles.get("content"))

    return files


def build_project_manifest(state: dict) -> Dict[str, Any]:
    """DSL consumed by page/app LLM: only listed exports/imports are allowed."""
    files = _collect_files_from_state(state)
    modules: List[Dict[str, Any]] = []

    for path in sorted(files.keys()):
        code = files[path]
        kind = _file_kind(path)
        exports = _parse_exports(code)
        default_export = _parse_default_export_name(code, path)
        named_exports = [name for name in exports if name != "default"]
        entry: Dict[str, Any] = {
            "path": path,
            "kind": kind,
            "exports": exports,
            "defaultExport": default_export,
            "namedExports": named_exports,
        }
        entry["importForms"] = _allowed_import_forms(path, exports, kind, default_export)
        imports = _parse_imports(code)
        if imports:
            entry["imports"] = imports
        modules.append(entry)

    ui = as_dict(state.get("ui"))
    pages = [
        {
            "pageId": p.get("pageId"),
            "route": p.get("route"),
            "layout": p.get("layout"),
            "path": f"/pages/{p.get('pageId')}.tsx" if p.get("pageId") else None,
        }
        for p in dict_list(ui, "pages")
    ]

    return {
        "version": 1,
        "dsl": "ProjectModuleManifest",
        "conventions": {
            "components": "default export; import as listed by module.importForms.default.example",
            "layouts": "default export; App.tsx must import layouts using module.importForms.default.example",
            "pages": "default export; App.tsx must import pages using module.importForms.default.example",
            "hooks": "named exports only; import from ../hooks/<file>",
            "services": "named async function exports only; never export filename as symbol (no TodoItemService class); hooks import only service.namedExports",
        },
        "rules": [
            "Only import modules listed in modules[].path.",
            "For App.tsx, use module.importForms.fromApp as the import specifier.",
            "Use default import only when module.defaultExport is not null.",
            "Use named imports only from module.namedExports.",
            "Never invent an export symbol, path, alias, or npm package.",
        ],
        "pages": pages,
        "modules": modules,
    }


def manifest_for_llm(state: dict) -> str:
    """Compact JSON string for human/LLM prompts."""
    manifest = build_project_manifest(state)
    return json.dumps(manifest, ensure_ascii=False, indent=2)


def manifest_for_file_map(file_map: Dict[str, str]) -> str:
    """Build manifest text from a flat path → content map (modification / debug flows)."""
    return manifest_for_llm({"files": {"files": file_map}})


def apply_file_map_to_state(state: dict, files: Dict[str, str]) -> dict:
    """Write repaired service/hooks files back into state."""
    updates: dict = {}

    def patch_files(state_key: str) -> None:
        block = as_dict(state.get(state_key))
        items = dict_list(block, "files")
        if not items:
            return
        changed = False
        for item in items:
            path = _normalize_path(item.get("path") or "")
            if path not in files:
                continue
            code = files[path]
            if "content" in item:
                item["content"] = code
            if "code" in item:
                item["code"] = code
            if "content" not in item and "code" not in item:
                item["content"] = code
            changed = True
        if changed:
            updates[state_key] = {**block, "files": items}

    patch_files("service")
    patch_files("hooks")
    return updates
