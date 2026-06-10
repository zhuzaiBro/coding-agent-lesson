"""
Modification 流程核心：按用户描述对 existingFiles 打补丁。

选取相关上下文文件 → LLM 输出 path/content 补丁 → apply_patches_to_file_map 合并。
不跑完整 19 节点，适合 Sandpack 上的增量编辑。
"""
from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.assembly.prompts.user_modify_prompts import (
    USER_MODIFY_SYSTEM_PROMPT,
)
from agents.flows.traditional.assembly.schemas.file_patch_schema import FilePatchResult
from agents.utils.apply_file_patches import apply_patches_to_file_map
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.file_patch_utils import paths_from_user_text, select_context_files
from agents.utils.model import get_structured_model
from agents.utils.project_manifest import manifest_for_file_map
from agents.utils.prompt_context import format_path_list
from agents.utils.retry import with_retry


def _file_map_to_manifest_items(file_map: dict) -> list:
    return [{"path": path, "content": content} for path, content in sorted(file_map.items())]


async def user_modify_node(state: dict) -> dict:
    """LLM-driven edits from the user's modification request."""
    print("--- UserModifyNode Start ---")

    assembled = state.get("files", {})
    if not isinstance(assembled, dict):
        return {}

    file_map = assembled.get("files", {})
    stats = assembled.get("stats", {}) or {}
    if not isinstance(file_map, dict) or not file_map:
        return {}

    user_request = (state.get("modificationRequest") or "").strip()
    if not user_request:
        print("[UserModify] Empty modification request, skipping")
        return {}

    priority = paths_from_user_text(user_request)
    context_files = select_context_files(
        file_map,
        priority_paths=priority,
        max_files=18,
    )
    manifest_text = state.get("projectManifestText") or ""

    human_parts = [
        "## User change request\n",
        user_request,
        "\n\n",
    ]
    if manifest_text:
        human_parts.append(f"## Project import manifest\n{manifest_text}\n\n")
    human_parts.append(
        format_path_list(_file_map_to_manifest_items(file_map), label="All project paths")
    )
    human_parts.append("\n## Files you may edit (full contents)\n")
    for path, content in context_files.items():
        human_parts.append(f"### {path}\n```tsx\n{content}\n```\n")

    structured_model = get_structured_model(FilePatchResult)
    messages = [
        SystemMessage(content=USER_MODIFY_SYSTEM_PROMPT),
        HumanMessage(content="".join(human_parts)),
    ]

    try:
        response = await with_retry(
            structured_model,
            messages,
            max_retries=2,
            on_retry=lambda attempt, err: print(f"[UserModify] Retry {attempt}: {err}"),
        )
        result_dict = response.model_dump() if hasattr(response, "model_dump") else response
        if isinstance(result_dict, dict):
            result_dict = normalize_llm_result(result_dict)
            result = FilePatchResult(**result_dict)
        else:
            result = response
    except Exception as error:
        print(f"[UserModify] LLM failed: {error}")
        return {
            "files": {
                "files": file_map,
                "stats": {
                    **stats,
                    "userModifyError": str(error)[:500],
                },
            }
        }

    patches = result.patches or []
    if not patches:
        print("[UserModify] No patches returned")
        return {
            "files": {
                "files": file_map,
                "stats": {
                    **stats,
                    "userModifySummary": result.summary or "no changes",
                },
            }
        }

    updated, applied = apply_patches_to_file_map(file_map, patches)

    return {
        "files": {
            "files": updated,
            "stats": {
                **stats,
                "userModifySummary": result.summary,
                "userModifyFilesPatched": applied,
                "compileChecked": False,
            },
        },
        "projectManifestText": manifest_for_file_map(updated),
    }
