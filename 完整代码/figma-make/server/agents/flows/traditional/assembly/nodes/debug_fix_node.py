"""Compile-debug fix node: LLM repairs files after failed compile check."""
import os
import re
from typing import Dict, List, Optional, Set

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.assembly.prompts.debug_fix_prompts import (
    DEBUG_FIX_SYSTEM_PROMPT,
)
from agents.flows.traditional.assembly.schemas.debug_fix_schema import DebugFixResult
from agents.utils.code_normalizer import normalize_code_content, normalize_llm_result
from agents.utils.export_repair import repair_all_exports
from agents.utils.model import get_structured_model
from agents.utils.prompt_context import format_path_list
from agents.utils.retry import with_retry


def _is_enabled() -> bool:
    return os.getenv("ENABLE_COMPILE_DEBUG_FIX", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _max_attempts() -> int:
    try:
        return max(0, int(os.getenv("FRONTEND_COMPILE_FIX_MAX_RETRIES", "2")))
    except ValueError:
        return 2


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def _paths_from_build_log(error: str) -> Set[str]:
    found: Set[str] = set()
    for match in re.finditer(
        r"(?:[/\\]?[\w.-]+)+[/\\][\w.-]+\.(?:tsx?|jsx?|css)",
        error,
    ):
        raw = match.group(0).replace("\\", "/")
        if raw.startswith("src/"):
            found.add(_normalize_path(raw[len("src/") :]))
        elif raw.startswith("/src/"):
            found.add(_normalize_path(raw[len("/src/") :]))
        else:
            found.add(_normalize_path(raw.lstrip("/")))
    return found


def _select_context_files(
    file_map: Dict[str, str],
    error: str,
    *,
    max_files: int = 14,
    max_chars_per_file: int = 12000,
) -> Dict[str, str]:
    priority_paths: List[str] = []
    for path in sorted(_paths_from_build_log(error)):
        if path in file_map:
            priority_paths.append(path)
        alt = _normalize_path(f"/src{path}") if not path.startswith("/src/") else path
        if alt in file_map and alt not in priority_paths:
            priority_paths.append(alt)

    code_paths = sorted(
        p
        for p in file_map
        if p.endswith((".ts", ".tsx", ".js", ".jsx", ".css"))
    )

    ordered: List[str] = []
    for path in priority_paths + ["/package.json", "/App.tsx", "/index.tsx"] + code_paths:
        if path in file_map and path not in ordered:
            ordered.append(path)
        if len(ordered) >= max_files:
            break

    selected: Dict[str, str] = {}
    for path in ordered[:max_files]:
        content = file_map[path]
        if len(content) > max_chars_per_file:
            content = content[:max_chars_per_file] + "\n/* ... truncated for debug fix ... */\n"
        selected[path] = content
    return selected


def _resolve_patch_path(path: str, file_map: Dict[str, str]) -> Optional[str]:
    normalized = _normalize_path(path)
    if normalized in file_map:
        return normalized
    if normalized.startswith("/src/"):
        root = _normalize_path(normalized[len("/src/") :])
        if root in file_map:
            return root
    src_path = f"/src{normalized}"
    if src_path in file_map:
        return src_path
    return None


def _file_map_to_manifest_items(file_map: Dict[str, str]) -> List[dict]:
    return [{"path": path, "content": content} for path, content in sorted(file_map.items())]


async def debug_fix_node(state: dict) -> dict:
    """Use LLM to fix build errors reported by compileCheckNode."""
    if not _is_enabled():
        print("[DebugFix] Disabled via ENABLE_COMPILE_DEBUG_FIX")
        return {}

    print("--- DebugFixNode Start ---")

    assembled = state.get("files", {})
    if not isinstance(assembled, dict):
        return {}

    file_map = assembled.get("files", {})
    stats = assembled.get("stats", {}) or {}
    if not isinstance(file_map, dict) or not file_map:
        return {}

    if stats.get("compileChecked"):
        print("[DebugFix] Build already passed, skipping")
        return {}

    compile_error = stats.get("compileError")
    if not compile_error:
        print("[DebugFix] No compileError in stats, skipping")
        return {}

    attempts = int(stats.get("compileFixAttempts") or 0)
    if attempts >= _max_attempts():
        print(f"[DebugFix] Max attempts reached ({attempts}), skipping")
        return {}

    context_files = _select_context_files(file_map, compile_error)
    manifest_text = state.get("projectManifestText") or ""

    human_parts = [
        f"## Build error (attempt {attempts + 1} of {_max_attempts()})\n",
        "```text",
        str(compile_error)[-8000:],
        "```\n",
    ]
    if manifest_text:
        human_parts.append(f"## Project import manifest\n{manifest_text}\n")
    human_parts.append(
        format_path_list(_file_map_to_manifest_items(file_map), label="All project paths")
    )
    human_parts.append("## Files to edit (full contents)\n")
    for path, content in context_files.items():
        human_parts.append(f"### {path}\n```tsx\n{content}\n```\n")

    structured_model = get_structured_model(DebugFixResult)
    messages = [
        SystemMessage(content=DEBUG_FIX_SYSTEM_PROMPT),
        HumanMessage(content="".join(human_parts)),
    ]

    try:
        response = await with_retry(
            structured_model,
            messages,
            max_retries=2,
            on_retry=lambda attempt, err: print(f"[DebugFix] Retry {attempt}: {err}"),
        )
        result_dict = response.model_dump() if hasattr(response, "model_dump") else response
        if isinstance(result_dict, dict):
            result_dict = normalize_llm_result(result_dict)
            result = DebugFixResult(**result_dict)
        else:
            result = response
    except Exception as error:
        print(f"[DebugFix] LLM fix failed: {error}")
        return {
            "files": {
                "files": file_map,
                "stats": {
                    **stats,
                    "compileFixAttempts": attempts + 1,
                    "compileFixError": str(error)[:500],
                },
            }
        }

    patches = result.patches or []
    if not patches:
        print("[DebugFix] Model returned no patches")
        return {
            "files": {
                "files": file_map,
                "stats": {
                    **stats,
                    "compileFixAttempts": attempts + 1,
                    "compileFixSummary": result.summary or "no patches",
                },
            }
        }

    updated = dict(file_map)
    applied = 0
    for patch in patches:
        resolved = _resolve_patch_path(patch.path, updated)
        if not resolved:
            print(f"[DebugFix] Skip unknown path: {patch.path}")
            continue
        updated[resolved] = normalize_code_content(patch.content)
        applied += 1
        print(f"[DebugFix] Patched {resolved}: {patch.reason or '(no reason)'}")

    export_stats = repair_all_exports(updated)

    new_stats = {
        **stats,
        "compileChecked": False,
        "compileFixAttempts": attempts + 1,
        "compileFixSummary": result.summary,
        "compileFixFilesPatched": applied,
        **export_stats,
    }
    new_stats.pop("compileError", None)

    print(f"[DebugFix] Applied {applied} patch(es), re-running compile check next")
    return {"files": {"files": updated, "stats": new_stats}}
