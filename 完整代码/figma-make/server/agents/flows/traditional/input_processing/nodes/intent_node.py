"""step1: Intent analysis node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.input_processing.prompts.intent_prompts import INTENT_SYSTEM_PROMPT
from agents.flows.traditional.input_processing.schemas.intent_schema import IntentResult
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


def _get_last_text(messages: list) -> str:
    if not messages:
        return ""
    last = messages[-1]
    if isinstance(last, dict):
        content = last.get("content", "")
    else:
        content = getattr(last, "content", "")
    return content if isinstance(content, str) else ""


async def intent_node(state: dict) -> dict:
    """Analyze product intent from user messages."""
    # MOCK MODE
    mock_result = await try_execute_mock(state, "intentNode", "intentResult.json", "intent")
    if mock_result:
        return mock_result

    print("--- IntentNode Start ---")

    structured_model = get_structured_model(IntentResult)

    # Get user message text
    user_text = _get_last_text(state.get("messages", []))
    analysis = state.get("analysis", {})
    summary = analysis.get("summary", "") if analysis else ""

    human_msg = f"""Please analyze the following user request and extract product intent:

User request: {user_text}

Analysis summary: {summary}"""

    prompt = [
        SystemMessage(content=INTENT_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[IntentNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    print("--- IntentNode End ---")

    return {"intent": result_dict}
