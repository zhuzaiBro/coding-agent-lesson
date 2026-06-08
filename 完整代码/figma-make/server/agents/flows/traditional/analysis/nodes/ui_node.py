"""step3: UI architecture analysis node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.analysis.prompts.ui_prompts import UI_SYSTEM_PROMPT
from agents.flows.traditional.analysis.schemas.ui_schema import UIResult
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


async def ui_node(state: dict) -> dict:
    """Design UI page architecture based on capabilities."""
    mock_result = await try_execute_mock(state, "uiNode", "uiResult.json", "ui")
    if mock_result:
        return mock_result

    print("--- UINode Start ---")

    structured_model = get_structured_model(UIResult)

    capabilities = state.get("capabilities", {})
    intent = state.get("intent", {})
    analysis = state.get("analysis", {})

    human_msg = f"""Design the UI architecture for this application:

Capabilities:
{json.dumps(capabilities, ensure_ascii=False, indent=2)}

Product Intent:
{json.dumps(intent, ensure_ascii=False, indent=2)}

Design Analysis: {analysis.get('designAnalysis', 'None')}
Analysis Tags: {', '.join(analysis.get('tags', []))}"""

    prompt = [
        SystemMessage(content=UI_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[UINode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    print("--- UINode End ---")

    return {"ui": result_dict}
