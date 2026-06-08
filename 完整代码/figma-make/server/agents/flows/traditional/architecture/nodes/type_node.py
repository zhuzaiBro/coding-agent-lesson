"""step7: Type generation node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.architecture.prompts.type_prompts import TYPE_SYSTEM_PROMPT
from agents.flows.traditional.architecture.schemas.type_schema import TypeGenerationResult
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


async def type_node(state: dict) -> dict:
    """Generate TypeScript type definition files."""
    mock_result = await try_execute_mock(state, "typeNode", "typeResult.json", "types")
    if mock_result:
        return mock_result

    print("--- TypeNode Start ---")

    structured_model = get_structured_model(TypeGenerationResult)

    capabilities = state.get("capabilities", {})
    data_models = capabilities.get("dataModels", []) if capabilities else []

    human_msg = f"""Generate TypeScript interface definitions for the following data models:

Data Models:
{json.dumps(data_models, ensure_ascii=False, indent=2)}

Create one .ts file per model in /types/ directory with proper TypeScript interfaces."""

    prompt = [
        SystemMessage(content=TYPE_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[TypeNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    print(f"--- TypeNode End ({len(result_dict.get('files', []))} files) ---")

    return {"types": result_dict}
