"""step11: Hooks generation node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.code_generation.prompts.hooks_prompts import HOOKS_SYSTEM_PROMPT
from agents.flows.traditional.code_generation.schemas.hooks_schema import HooksResult
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.mock import try_execute_mock
from agents.utils.prompt_context import (
    format_files_with_exports,
    format_path_list,
    hook_import_manifest,
    service_export_catalog,
    type_import_manifest,
)
from agents.utils.state_helpers import as_dict, dict_list
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry
from agents.utils.supabase_integration import format_supabase_prompt_block


async def hooks_node(state: dict) -> dict:
    """Generate custom React hooks."""
    mock_result = await try_execute_mock(state, "hooksNode", "hooksResult.json", "hooks")
    if mock_result:
        return mock_result

    print("--- HooksNode Start ---")

    structured_model = get_structured_model(HooksResult)

    service = as_dict(state.get("service"))
    types = as_dict(state.get("types"))

    service_files = dict_list(service, "files")
    type_files = dict_list(types, "files")

    human_msg = f"""Generate custom React hooks that wrap these service functions.

{format_path_list(service_files, label="Service files (one hook per file)")}
{format_path_list(type_files, label="Type files")}

Service import manifest (hooks MUST use ONLY these import paths — no other ../services/*):
{hook_import_manifest(service_files)}

{service_export_catalog(service_files)}

{format_files_with_exports(type_files, label="Type files export inventory", path_prefix="/types/")}

Type import manifest:
{type_import_manifest(type_files)}

Service summaries:
{json.dumps([{'path': f.get('path'), 'description': f.get('description')} for f in service_files], ensure_ascii=False, indent=2)}

Each hook: data + loading + error states. Use ONLY allowedSymbols from the Service export catalog; never import the service filename as a symbol.
{format_supabase_prompt_block(state.get("supabase"))}"""

    prompt = [
        SystemMessage(content=HOOKS_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[HooksNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = normalize_llm_result(result_dict) or {}
    files = dict_list(result_dict, "files")
    print(f"--- HooksNode End ({len(files)} files) ---")

    return {"hooks": result_dict}
