"""step4: Component contract definition node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.analysis.prompts.component_prompts import COMPONENT_SYSTEM_PROMPT
from agents.flows.traditional.analysis.schemas.component_schema import ComponentResult
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


async def component_node(state: dict) -> dict:
    """Define component contracts based on UI architecture."""
    mock_result = await try_execute_mock(state, "componentNode", "componentResult.json", "components")
    if mock_result:
        return mock_result

    print("--- ComponentNode Start ---")

    structured_model = get_structured_model(ComponentResult)

    ui = state.get("ui", {})
    capabilities = state.get("capabilities", {})
    intent = state.get("intent", {})

    human_msg = f"""Define component contracts for the following UI architecture:

UI Architecture:
{json.dumps(ui, ensure_ascii=False, indent=2)}

Data Models & Behaviors:
{json.dumps(capabilities, ensure_ascii=False, indent=2)}

Product Context:
{json.dumps(intent, ensure_ascii=False, indent=2)}"""

    prompt = [
        SystemMessage(content=COMPONENT_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[ComponentNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    print("--- ComponentNode End ---")

    return {"components": result_dict}
