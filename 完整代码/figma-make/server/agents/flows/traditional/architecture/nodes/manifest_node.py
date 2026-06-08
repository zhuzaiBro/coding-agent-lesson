"""Build project DSL manifest and sync hook/service exports before page assembly."""
import json

from agents.utils.export_repair import repair_all_exports
from agents.utils.project_manifest import (
    apply_file_map_to_state,
    build_project_manifest,
    _collect_files_from_state,
)


async def manifest_node(state: dict) -> dict:
    """
    Deterministic node (no LLM):
    1. Flatten generated modules into a virtual file map
    2. Repair hook ↔ service export mismatches
    3. Emit projectManifest DSL for page/app generators
    """
    print("--- ManifestNode Start ---")

    files = _collect_files_from_state(state)
    repair_stats = repair_all_exports(files)
    state_updates = apply_file_map_to_state(state, files)

    merged_state = {**state, **state_updates}
    manifest = build_project_manifest(merged_state)
    module_count = len(manifest.get("modules", []))

    if any(repair_stats.get(k, 0) > 0 for k in repair_stats):
        print(f"[ManifestNode] Export sync: {repair_stats}")

    print(f"[ManifestNode] DSL ready ({module_count} modules)")
    print("--- ManifestNode End ---")

    return {
        **state_updates,
        "projectManifest": manifest,
        "projectManifestText": json.dumps(manifest, ensure_ascii=False, indent=2),
    }
