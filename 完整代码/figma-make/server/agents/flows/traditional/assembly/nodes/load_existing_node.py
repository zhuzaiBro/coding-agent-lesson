"""Load existing project files for modification flow."""
from typing import Dict

from agents.adapters.route_helpers import get_last_text
from agents.utils.project_manifest import manifest_for_file_map


def _normalize_input_files(raw: object) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    result: Dict[str, str] = {}
    for path, content in raw.items():
        if not isinstance(path, str):
            continue
        if isinstance(content, str):
            result[path] = content
        elif isinstance(content, dict) and isinstance(content.get("code"), str):
            result[path] = content["code"]
    return result


async def load_existing_node(state: dict) -> dict:
    """Merge client-provided files with checkpoint state."""
    print("--- LoadExistingNode Start ---")

    from_input = _normalize_input_files(state.get("existingFiles"))
    assembled = state.get("files", {})
    from_checkpoint: Dict[str, str] = {}
    if isinstance(assembled, dict):
        raw = assembled.get("files", {})
        if isinstance(raw, dict):
            from_checkpoint = {
                k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, str)
            }

    merged = {**from_checkpoint, **from_input}
    if not merged:
        raise ValueError(
            "Modification flow requires existing project files. "
            "Send `files` in the request body or use the same projectId after a full generation."
        )

    request_text = get_last_text(state.get("messages", []))
    manifest_text = manifest_for_file_map(merged)

    print(f"[LoadExisting] Loaded {len(merged)} files for modification")

    return {
        "files": {
            "files": merged,
            "stats": {
                "totalFiles": len(merged),
                "routeType": "modification",
            },
        },
        "projectManifestText": manifest_text,
        "modificationRequest": request_text,
        "modification": {
            "fileCount": len(merged),
            "summary": request_text[:500] if request_text else "User modification",
        },
    }
