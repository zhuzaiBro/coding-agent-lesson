"""step0: Behavior analysis node."""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.flows.traditional.analysis.prompts.analysis_prompts import ANALYSIS_SYSTEM_PROMPT
from agents.flows.traditional.analysis.schemas.analysis_schema import AnalysisResult
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


def _convert_messages(raw_messages: list) -> list:
    """Convert frontend message format to LangChain message objects (text only)."""
    result = []
    for msg in raw_messages:
        if isinstance(msg, dict):
            content = msg.get("content", "")
            role = msg.get("role", "user")
        else:
            content = getattr(msg, "content", "")
            role = getattr(msg, "role", "user")

        text = content if isinstance(content, str) and content.strip() else "User uploaded an attachment"

        if role == "user":
            result.append(HumanMessage(content=text))
        else:
            result.append(AIMessage(content=text))
    return result


async def analysis_node(state: dict) -> dict:
    """Analyze user intent from messages."""
    structured_model = get_structured_model(AnalysisResult)

    messages = []
    if state.get("messages") and isinstance(state["messages"], list):
        last_msg = state["messages"][-1]
        messages = _convert_messages([last_msg])

    prompt = [SystemMessage(content=ANALYSIS_SYSTEM_PROMPT)] + messages

    print("\n[AnalysisNode] Starting intent analysis")

    # MOCK MODE
    mock_result = await try_execute_mock(state, "analysisNode", "analysisResult.json", "analysis")
    if mock_result:
        analysis = mock_result.get("analysis", {})
        print(
            f"[AnalysisNode] needsDatabase={analysis.get('needsDatabase')} "
            f"({analysis.get('databaseReason') or 'n/a'})"
        )
        return {
            **mock_result,
            "skipGeneration": analysis.get("type") in ("QA", "CHIT_CHAT"),
        }

    print("--- User Message Analysis Start ---")

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[AnalysisNode] Retry {attempt}: {err}"),
    )

    print("--- User Message Analysis End ---")

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    print(f"[AnalysisNode] User intent: {result_dict.get('type')}")
    print(
        f"[AnalysisNode] needsDatabase={result_dict.get('needsDatabase')} "
        f"({result_dict.get('databaseReason') or 'n/a'})"
    )

    return {
        "analysis": result_dict,
        "skipGeneration": result_dict.get("type") in ("QA", "CHIT_CHAT"),
    }
