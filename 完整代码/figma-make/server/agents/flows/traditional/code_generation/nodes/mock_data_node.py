"""step9: Mock data generation node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.code_generation.prompts.mock_data_prompts import MOCK_DATA_SYSTEM_PROMPT
from agents.flows.traditional.code_generation.schemas.mock_data_schema import MockDataResult
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.mock import try_execute_mock
from agents.utils.state_helpers import as_dict, dict_list
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


async def mock_data_node(state: dict) -> dict:
    """Generate mock data files for the application."""
    mock_result = await try_execute_mock(state, "mockDataNode", "mockDataResult.json", "mockData")
    if mock_result:
        return mock_result

    print("--- MockDataNode Start ---")

    structured_model = get_structured_model(MockDataResult)

    capabilities = as_dict(state.get("capabilities"))
    types = as_dict(state.get("types"))
    data_models = dict_list(capabilities, "dataModels")
    type_files = dict_list(types, "files")

    types_context = ""
    if type_files:
        types_context = "\n\nType definitions already generated:\n" + "\n".join(
            f"- {f.get('path')}: {f.get('modelId')} interface" for f in type_files[:5]
        )

    human_msg = f"""Generate mock data files for these data models:

Data Models:
{json.dumps(data_models, ensure_ascii=False, indent=2)}{types_context}

Generate realistic sample data with 5-10 records per model. Group related models in the same file where appropriate."""

    prompt = [
        SystemMessage(content=MOCK_DATA_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[MockDataNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = normalize_llm_result(result_dict) or {}
    files = dict_list(result_dict, "files")
    print(f"--- MockDataNode End ({len(files)} files) ---")

    return {"mockData": result_dict}
