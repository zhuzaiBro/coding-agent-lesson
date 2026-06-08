"""step15: App.tsx generation node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.assembly.prompts.app_gen_prompts import APP_GEN_SYSTEM_PROMPT
from agents.flows.traditional.assembly.schemas.app_gen_schema import AppGenResult
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.project_manifest import build_project_manifest
from agents.utils.retry import with_retry
from agents.utils.state_helpers import as_dict, as_dict_list, dict_list


def _route_import_entries(manifest: dict) -> list[dict]:
    entries: list[dict] = []
    for module in manifest.get("modules", []):
        kind = module.get("kind")
        if kind not in {"page", "layout"}:
            continue
        default_export = module.get("defaultExport")
        import_forms = module.get("importForms") or {}
        from_app = import_forms.get("fromApp")
        if not default_export or not from_app:
            continue
        entries.append(
            {
                "kind": kind,
                "path": module.get("path"),
                "defaultExport": default_export,
                "importFromApp": from_app,
                "importStatement": f"import {default_export} from '{from_app}';",
                "namedExports": module.get("namedExports", []),
            }
        )
    return entries


async def app_gen_node(state: dict) -> dict:
    """Generate App.tsx with routing configuration."""
    mock_result = await try_execute_mock(state, "appGenNode", "appGenResult.json", "app")
    if mock_result:
        return mock_result

    print("--- AppGenNode Start ---")

    structured_model = get_structured_model(AppGenResult)

    ui = as_dict(state.get("ui"))
    layouts = as_dict(state.get("layouts"))
    pages_code = as_dict_list(state.get("pagesCode"))

    pages = dict_list(ui, "pages")
    route_structure = as_dict(layouts.get("routeStructure"))
    layouts_code = dict_list(layouts, "layoutsCode")

    # Build page routes context
    pages_context = []
    for page in pages:
        react_path = page.get("route", "/").replace("[", ":").replace("]", "")
        pages_context.append(f"- {page.get('pageId')}: {react_path}")

    # Build generated pages context
    generated_pages = []
    for p in pages_code:
        path = p.get("path", "")
        import re
        match = re.search(r"/pages/([^.]+)\.tsx$", path)
        if match:
            generated_pages.append(f"- {match.group(1)} ({path})")

    # Detect providers needed
    dependency = as_dict(state.get("dependency"))
    pkg_deps = as_dict(as_dict(dependency.get("packageJson")).get("dependencies"))
    provider_hints = []
    if "sonner" in pkg_deps:
        provider_hints.append("- sonner: add <Toaster /> from 'sonner' at App root")
    if "react-hot-toast" in pkg_deps:
        provider_hints.append("- react-hot-toast: add <Toaster /> at App root")
    if "@tanstack/react-query" in pkg_deps:
        provider_hints.append("- react-query: wrap with QueryClientProvider")

    app_manifest = build_project_manifest(state)
    manifest_text = json.dumps(app_manifest, ensure_ascii=False, indent=2)
    route_imports = _route_import_entries(app_manifest)

    human_msg = f"""Generate App.tsx for this React + React Router v6 application:

ProjectModuleManifest DSL (authoritative; import only listed modules/exports):
{manifest_text or '(not available)'}

Route Import Table (App.tsx MUST copy these import paths and export styles exactly):
{json.dumps(route_imports, ensure_ascii=False, indent=2)}

Pages and Routes:
{chr(10).join(pages_context)}

Generated Page Components:
{chr(10).join(generated_pages) if generated_pages else '(same as above)'}

Layout Components:
{json.dumps([l.get('path') for l in layouts_code], ensure_ascii=False)}

Route Structure (Layout -> Pages):
{json.dumps(route_structure, ensure_ascii=False, indent=2)}

Required Providers:
{chr(10).join(provider_hints) if provider_hints else 'None required'}

Hard rules:
- Import pages/layouts only from Route Import Table.
- Use default import only when `defaultExport` is present.
- Do not use named imports for page/layout modules unless `namedExports` explicitly lists the symbol.
- Do not invent files, exports, aliases, or npm packages.
- Import styles with `import './styles.css';` when /styles.css exists in the manifest.

Generate a complete App.tsx using BrowserRouter + Routes with nested route structure."""

    prompt = [
        SystemMessage(content=APP_GEN_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[AppGenNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = normalize_llm_result(result_dict)
    print("--- AppGenNode End ---")

    return {"app": result_dict}
