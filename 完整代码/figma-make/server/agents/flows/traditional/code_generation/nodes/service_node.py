"""step10: Service layer generation node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.code_generation.prompts.service_prompt import SERVICE_SYSTEM_PROMPT
from agents.flows.traditional.code_generation.schemas.service_schema import ServiceResult
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.mock import try_execute_mock
from agents.utils.prompt_context import (
    expected_service_paths,
    format_files_with_exports,
    format_path_list,
    mock_import_manifest,
    type_import_manifest,
)
from agents.utils.state_helpers import as_dict, dict_list
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry
from agents.utils.supabase_integration import format_supabase_prompt_block


async def service_node(state: dict) -> dict:
    """Generate service layer files."""
    mock_result = await try_execute_mock(state, "serviceNode", "serviceResult.json", "service")
    if mock_result:
        return mock_result

    print("--- ServiceNode Start ---")

    structured_model = get_structured_model(ServiceResult)

    mock_data = as_dict(state.get("mockData"))
    types = as_dict(state.get("types"))
    capabilities = as_dict(state.get("capabilities"))

    mock_files = dict_list(mock_data, "files")
    type_files = dict_list(types, "files")
    behaviors = dict_list(capabilities, "behaviors")

    required_services = expected_service_paths(mock_files)

    human_msg = f"""Generate service layer files that wrap the mock data.

{format_path_list(mock_files, label="Mock data files (create one service per file)")}
{format_path_list(type_files, label="Type files")}

Required service paths (use exactly these paths):
{chr(10).join(f"  - {p}" for p in required_services) if required_services else "  (derive from mock paths: /data/{{stem}}.ts → /services/{{stem}}Service.ts)"}

{format_files_with_exports(mock_files, label="Mock data files export inventory", path_prefix="/data/")}

Mock import manifest (services MUST use only these imports):
{mock_import_manifest(mock_files)}

{format_files_with_exports(type_files, label="Type files export inventory", path_prefix="/types/")}

Type import manifest:
{type_import_manifest(type_files)}

Required Behaviors:
{json.dumps([{'id': b.get('behaviorId'), 'description': b.get('description')} for b in behaviors], ensure_ascii=False, indent=2)}

Create service functions for each behavior. Do not add files beyond the required service paths.
{format_supabase_prompt_block(state.get("supabase"))}"""

    prompt = [
        SystemMessage(content=SERVICE_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[ServiceNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = normalize_llm_result(result_dict) or {}
    files = dict_list(result_dict, "files")
    print(f"--- ServiceNode End ({len(files)} files) ---")

    return {"service": result_dict}
