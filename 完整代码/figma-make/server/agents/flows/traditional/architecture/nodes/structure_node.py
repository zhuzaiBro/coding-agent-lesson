"""step5: Project structure definition node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.architecture.prompts.structure_prompts import STRUCTURE_SYSTEM_PROMPT
from agents.flows.traditional.architecture.schemas.structure_schema import StructureResult
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry
from agents.utils.state_helpers import as_dict, dict_list


async def structure_node(state: dict) -> dict:
    """Define project file structure."""
    mock_result = await try_execute_mock(state, "structureNode", "structureResult.json", "structure")
    if mock_result:
        return mock_result

    print("--- StructureNode Start ---")

    structured_model = get_structured_model(StructureResult)

    components = as_dict(state.get("components"))
    capabilities = as_dict(state.get("capabilities"))
    ui = as_dict(state.get("ui"))

    comp_list = dict_list(components, "components")
    pages = dict_list(ui, "pages")
    data_models = dict_list(capabilities, "dataModels")

    human_msg = f"""Define the complete file structure for this React project:

Components to generate ({len(comp_list)}):
{json.dumps([c.get('componentId') for c in comp_list], ensure_ascii=False)}

Pages ({len(pages)}):
{json.dumps([p.get('pageId') for p in pages], ensure_ascii=False)}

Data Models ({len(data_models)}):
{json.dumps([m.get('modelId') for m in data_models], ensure_ascii=False)}

Include all necessary files: types, data, services, hooks, lib/utils, components, pages, layouts, App.tsx."""

    prompt = [
        SystemMessage(content=STRUCTURE_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[StructureNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    print("--- StructureNode End ---")

    return {"structure": result_dict}
