"""应用 LLM 文件补丁并执行 export 修复。"""
from typing import Dict, List

from agents.flows.traditional.assembly.schemas.file_patch_schema import FilePatch
from agents.utils.code_normalizer import normalize_code_content
from agents.utils.export_repair import repair_all_exports
from agents.utils.file_patch_utils import resolve_patch_path


def apply_patches_to_file_map(
    file_map: Dict[str, str],
    patches: List[FilePatch],
) -> tuple[Dict[str, str], int]:
    updated = dict(file_map)
    applied = 0
    for patch in patches:
        resolved = resolve_patch_path(patch.path, updated)
        if not resolved:
            print(f"[FilePatch] 跳过未知路径: {patch.path}")
            continue
        updated[resolved] = normalize_code_content(patch.content)
        applied += 1
        print(f"[FilePatch] 已修补 {resolved}: {patch.reason or '(无原因)'}")
    repair_all_exports(updated)
    return updated, applied
