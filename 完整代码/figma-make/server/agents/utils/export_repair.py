"""根据 service 实际导出修复 hook import（确定性，无 LLM）。"""
import re
from typing import Dict, List, Optional, Set, Tuple

HOOK_IMPORT_RE = re.compile(
    r"""import\s+\{([^}]+)\}\s+from\s+['"]\.\./services/([^'"]+)['"]""",
    re.MULTILINE,
)
EXPORT_FN_RE = re.compile(
    r"""export\s+(?:async\s+)?function\s+(\w+)""",
    re.MULTILINE,
)
EXPORT_CONST_RE = re.compile(
    r"""export\s+const\s+(\w+)""",
    re.MULTILINE,
)
EXPORT_BRACE_RE = re.compile(
    r"""export\s*\{([^}]+)\}""",
    re.MULTILINE,
)


def _service_path(stem: str) -> str:
    for prefix in ("/services/", "services/"):
        for ext in (".ts", ".tsx"):
            candidate = f"{prefix}{stem}{ext}"
            if candidate.startswith("/"):
                return candidate
    return f"/services/{stem}.ts"


def _normalize_assemble_path(path: str) -> str:
    p = path.replace("\\", "/")
    if not p.startswith("/"):
        p = f"/{p}"
    return p


def _find_service_file(files: Dict[str, str], stem: str) -> Tuple[str, str]:
    for path, content in files.items():
        normalized = _normalize_assemble_path(path)
        if normalized.endswith(f"/services/{stem}.ts") or normalized.endswith(
            f"/services/{stem}.tsx"
        ):
            return normalized, content
    target = _normalize_assemble_path(_service_path(stem))
    return target, files.get(target, "")


def _parse_export_brace_names(block: str) -> Set[str]:
    """解析 `export { a, b as c }` 暴露的名称（`as` 右侧为对外名称）。"""
    names: Set[str] = set()
    for part in (block or "").split(","):
        segment = part.strip()
        if not segment:
            continue
        if " as " in segment:
            _, alias = segment.rsplit(" as ", 1)
            names.add(alias.strip())
        else:
            names.add(segment.strip())
    return names


def _parse_exports(content: str) -> Set[str]:
    names: Set[str] = set()
    text = content or ""
    names.update(EXPORT_FN_RE.findall(text))
    names.update(EXPORT_CONST_RE.findall(text))
    for block in EXPORT_BRACE_RE.findall(text):
        names.update(_parse_export_brace_names(block))
    return names


def parse_named_exports(content: str) -> List[str]:
    """排序后的公开 named export 符号（函数、const、re-export）。"""
    return sorted(_parse_exports(content or ""))


def _guess_alias(missing: str, exports: Set[str]) -> str | None:
    if missing in exports:
        return missing
    lower_missing = missing.lower()
    for name in exports:
        if name.lower() == lower_missing:
            return name

    # getTasks → getAllTasks / listTasks / fetchTasks 等别名猜测
    if lower_missing.startswith("get"):
        suffix = lower_missing[3:]
        candidates = [
            f"getAll{suffix}",
            f"get{suffix}",
            f"list{suffix}",
            f"fetch{suffix}",
            f"find{suffix}",
        ]
        for cand in candidates:
            for name in exports:
                if name.lower() == cand.lower():
                    return name

    if lower_missing.startswith("toggle"):
        for name in exports:
            lower_name = name.lower()
            if lower_name.startswith("update") or "toggle" in lower_name or "complete" in lower_name:
                return name

    if "bystatus" in lower_missing or lower_missing.endswith("status"):
        base = lower_missing.replace("bystatus", "").replace("status", "")
        for cand in (
            f"get{base}ByStatus",
            f"list{base}ByStatus",
            f"filter{base}ByStatus",
            f"filter{base}",
        ):
            for name in exports:
                if name.lower() == cand.lower():
                    return name

    for name in exports:
        if lower_missing in name.lower() or name.lower() in lower_missing:
            return name
    return None


def _stub_export_function(name: str, exports: Set[str]) -> Optional[str]:
    """当 hook import 了缺失的 service API 时，合成最小 export 桩。"""
    lower = name.lower()
    update_fn = next((e for e in exports if e.lower().startswith("update")), None)
    list_fn = next(
        (e for e in exports if e.lower().startswith("get") or e.lower().startswith("list")),
        None,
    )

    if lower.startswith("toggle") and update_fn:
        return (
            f"export async function {name}(id: string, completed: boolean = true) {{\n"
            f"  return {update_fn}(id, {{ completed }} as any);\n"
            f"}}"
        )

    if ("bystatus" in lower or lower.endswith("status")) and list_fn:
        return (
            f"export async function {name}(status: string) {{\n"
            f"  const items = await {list_fn}();\n"
            f"  return items.filter((item: any) => item?.status === status);\n"
            f"}}"
        )

    if lower.startswith("get") and list_fn and name not in exports:
        return (
            f"export async function {name}(...args: any[]) {{\n"
            f"  return {list_fn}(...args);\n"
            f"}}"
        )
    return None


def _append_reexports(service_content: str, aliases: List[Tuple[str, str]]) -> str:
    if not aliases:
        return service_content
    existing = _parse_exports(service_content)
    lines = [service_content.rstrip(), "", "// 自动修复：为 hook import 补充 re-export"]
    for hook_name, service_name in aliases:
        if hook_name == service_name or hook_name in existing:
            continue
        if service_name not in existing:
            continue
        lines.append(f"export {{ {service_name} as {hook_name} }};")
        existing.add(hook_name)
    if len(lines) <= 3:
        return service_content
    lines.append("")
    return "\n".join(lines)


def _append_stub_exports(service_content: str, stubs: List[str]) -> str:
    if not stubs:
        return service_content
    lines = [service_content.rstrip(), "", "// 自动修复：为 hook import 补充桩 export"]
    lines.extend(stubs)
    lines.append("")
    return "\n".join(lines)


DEFAULT_IMPORT_RE = re.compile(
    r"""import\s+(\w+)\s+from\s+['"](\.\./(?:components|layouts|pages)/[^'"]+)['"]""",
    re.MULTILINE,
)
NAMED_COMPONENT_IMPORT_RE = re.compile(
    r"""import\s+\{\s*(\w+)\s*\}\s+from\s+['"](\.\./(?:components|layouts|pages)/[^'"]+)['"]""",
    re.MULTILINE,
)
HAS_DEFAULT_EXPORT_RE = re.compile(r"""export\s+default\b""")
NAMED_EXPORT_SYMBOL_RE = re.compile(
    r"""export\s+(?:async\s+)?function\s+(\w+)|export\s+const\s+(\w+)\s*=""",
    re.MULTILINE,
)


def _resolve_module_path(files: Dict[str, str], import_spec: str) -> str:
    """将 ../components/Foo 解析为 /components/Foo.tsx。"""
    spec = import_spec.replace("\\", "/")
    if spec.startswith("../"):
        spec = spec[3:]
    if not spec.startswith("/"):
        spec = f"/{spec}"
    for ext in (".tsx", ".ts", ".jsx", ".js"):
        candidate = f"{spec}{ext}"
        normalized = _normalize_assemble_path(candidate)
        if normalized in files:
            return normalized
        for path in files:
            if _normalize_assemble_path(path) == normalized:
                return path
    return _normalize_assemble_path(f"{spec}.tsx")


def _has_named_export(content: str, symbol: str) -> bool:
    for match in NAMED_EXPORT_SYMBOL_RE.finditer(content or ""):
        name = match.group(1) or match.group(2)
        if name == symbol:
            return True
    return False


def _append_default_export(content: str, symbol: str) -> str:
    if HAS_DEFAULT_EXPORT_RE.search(content or ""):
        return content
    if not _has_named_export(content, symbol):
        return content
    return content.rstrip() + f"\n\nexport default {symbol};\n"


def repair_component_default_exports(files: Dict[str, str]) -> Dict[str, int]:
    """当 import 方使用 default import 时，为目标文件补充缺失的 `export default`。"""
    patched = 0
    default_exports_added = 0

    importers: List[Tuple[str, str, str]] = []
    for path, code in files.items():
        if not path.endswith((".tsx", ".ts", ".jsx", ".js")):
            continue
        for match in DEFAULT_IMPORT_RE.finditer(code or ""):
            symbol, import_spec = match.groups()
            importers.append((path, symbol, import_spec))

    for _importer, symbol, import_spec in importers:
        target_path = _resolve_module_path(files, import_spec)
        target_content = files.get(target_path, "")
        if not target_content:
            continue
        if HAS_DEFAULT_EXPORT_RE.search(target_content):
            continue
        updated = _append_default_export(target_content, symbol)
        if updated != target_content:
            files[target_path] = updated
            patched += 1
            default_exports_added += 1

    return {
        "componentsPatched": patched,
        "defaultExportsAdded": default_exports_added,
    }


def repair_named_component_imports(files: Dict[str, str]) -> Dict[str, int]:
    """当目标仅有 default export 时，将 `import { Foo }` 改为 `import Foo`。"""
    imports_fixed = 0

    for path, code in list(files.items()):
        if not path.endswith((".tsx", ".ts", ".jsx", ".js")):
            continue
        updated = code
        for match in NAMED_COMPONENT_IMPORT_RE.finditer(code or ""):
            symbol, import_spec = match.groups()
            target_path = _resolve_module_path(files, import_spec)
            target_content = files.get(target_path, "")
            if not target_content or not HAS_DEFAULT_EXPORT_RE.search(target_content):
                continue
            if _has_named_export(target_content, symbol):
                continue
            old = match.group(0)
            new = f"import {symbol} from '{import_spec}'"
            updated = updated.replace(old, new, 1)
            imports_fixed += 1
        if updated != code:
            files[path] = updated

    return {"namedImportsFixed": imports_fixed}


def repair_hook_service_class_imports(files: Dict[str, str]) -> Dict[str, int]:
    """
    Hook 常错误 import `{ TodoItemService }`（文件名），而 service 实际导出的是函数。
    重写为 import 真实 named export，并去掉 `ServiceSymbol.` 前缀。
    """
    hooks_fixed = 0

    for path, code in list(files.items()):
        if not path.endswith((".ts", ".tsx")):
            continue
        if "/hooks/" not in path.replace("\\", "/"):
            continue

        updated = code or ""
        for match in HOOK_IMPORT_RE.finditer(code or ""):
            imported_raw, service_stem = match.groups()
            imported = [
                n.strip().split(" as ")[0].strip()
                for n in imported_raw.split(",")
                if n.strip()
            ]
            service_path, service_content = _find_service_file(files, service_stem)
            if not service_content:
                continue

            exports = _parse_exports(service_content)
            if not exports:
                continue

            invalid = [n for n in imported if n not in exports]
            if not invalid:
                continue

            looks_like_class = any(
                n == service_stem or n.endswith("Service") for n in invalid
            )
            if not looks_like_class:
                continue

            valid = [n for n in imported if n in exports]
            symbols = sorted(set(valid) | exports)
            old = match.group(0)
            new = f"import {{ {', '.join(symbols)} }} from '../services/{service_stem}'"
            if old.rstrip().endswith(";"):
                new += ";"
            if old in updated:
                updated = updated.replace(old, new, 1)
                hooks_fixed += 1

            for sym in invalid:
                updated = re.sub(rf"\b{re.escape(sym)}\.", "", updated)

        if updated != code:
            files[path] = updated

    return {"hookClassImportsFixed": hooks_fixed}


def repair_all_exports(files: Dict[str, str]) -> Dict[str, int]:
    """依次执行全部 export/import 修复并汇总统计。"""
    stats: Dict[str, int] = {}
    for part in (
        repair_hook_service_class_imports(files),
        repair_hook_service_exports(files),
        repair_component_default_exports(files),
        repair_named_component_imports(files),
    ):
        stats.update(part)
    return stats


def repair_hook_service_exports(files: Dict[str, str]) -> Dict[str, int]:
    """当 hook import 了 service 中不存在的符号时，补充 re-export 或桩函数。"""
    repaired_files = 0
    alias_count = 0

    for path, code in list(files.items()):
        if not path.endswith((".ts", ".tsx")):
            continue
        if "/hooks/" not in path.replace("\\", "/"):
            continue

        for match in HOOK_IMPORT_RE.finditer(code or ""):
            imported_raw, service_stem = match.groups()
            imported = [n.strip() for n in imported_raw.split(",") if n.strip()]
            service_path, service_content = _find_service_file(files, service_stem)
            if not service_content:
                continue

            exports = _parse_exports(service_content)
            aliases: List[Tuple[str, str]] = []
            stubs: List[str] = []
            for name in imported:
                if name in exports:
                    continue
                alias = _guess_alias(name, exports)
                if alias and alias != name:
                    aliases.append((name, alias))
                    exports.add(name)
                    continue
                stub = _stub_export_function(name, exports)
                if stub:
                    stubs.append(stub)
                    exports.add(name)

            updated = service_content
            if aliases:
                updated = _append_reexports(updated, aliases)
                alias_count += len(aliases)
            if stubs:
                updated = _append_stub_exports(updated, stubs)
                alias_count += len(stubs)

            if updated != service_content:
                files[service_path] = updated
                repaired_files += 1
                exports = _parse_exports(updated)

    return {"servicesPatched": repaired_files, "reexportsAdded": alias_count}
