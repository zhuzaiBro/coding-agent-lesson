"""step2: Capability analysis node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.analysis.prompts.capability_prompts import CAPABILITY_SYSTEM_PROMPT
from agents.flows.traditional.analysis.schemas.capability_schema import CapabilityResult
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


async def capability_node(state: dict) -> dict:
    """Analyze technical capabilities from product intent."""
    mock_result = await try_execute_mock(state, "capabilityNode", "capabilityResult.json", "capabilities")
    if mock_result:
        return mock_result

    print("--- CapabilityNode Start ---")

    structured_model = get_structured_model(CapabilityResult)

    intent = state.get("intent", {})
    analysis = state.get("analysis", {})

    human_msg = f"""Based on the following product intent, design the application's technical capabilities (pages, behaviors, data models):

Product Intent:
{json.dumps(intent, ensure_ascii=False, indent=2)}

Analysis Context:
- Summary: {analysis.get('summary', '')}
- Complexity: {analysis.get('complexity', 'MEDIUM')}
- Design Analysis: {analysis.get('designAnalysis', 'None')}"""

    prompt = [
        SystemMessage(content=CAPABILITY_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[CapabilityNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    print("--- CapabilityNode End ---")

    return {"capabilities": result_dict}
