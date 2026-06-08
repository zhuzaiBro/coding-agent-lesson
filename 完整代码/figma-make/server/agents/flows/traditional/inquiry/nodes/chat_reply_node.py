"""Conversational reply — plain QA/CHIT_CHAT or passthrough from database inquiry."""
from langchain_core.messages import HumanMessage, SystemMessage

from agents.adapters.route_helpers import get_last_text
from agents.flows.traditional.inquiry.prompts.inquiry_prompts import CHAT_REPLY_SYSTEM_PROMPT
from agents.flows.traditional.inquiry.schemas.chat_reply_schema import ChatReplyResult
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


async def chat_reply_node(state: dict) -> dict:
    """Emit chatReply SSE payload for frontend conversational UI."""
    inquiry = state.get("inquiry")
    if inquiry and inquiry.get("message"):
        print("[ChatReplyNode] Passthrough database inquiry answer")
        return {
            "chatReply": {
                "message": inquiry["message"],
                "inquiry": inquiry,
            }
        }

    mock_result = await try_execute_mock(
        state,
        "chatReplyNode",
        "chatReplyResult.json",
        "chatReply",
    )
    if mock_result:
        return mock_result

    print("--- ChatReplyNode Start ---")

    user_text = get_last_text(state.get("messages", []))
    analysis = state.get("analysis") or {}

    human = f"""User message:
{user_text}

Intent analysis:
{analysis.get('summary', '')}
Type: {analysis.get('type', '')}
"""

    model = get_structured_model(ChatReplyResult)
    result = await with_retry(
        model,
        [SystemMessage(content=CHAT_REPLY_SYSTEM_PROMPT), HumanMessage(content=human)],
        max_retries=2,
        on_retry=lambda attempt, err: print(f"[ChatReplyNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    message = str(result_dict.get("message") or "").strip() or "你好，有什么可以帮你的？"

    print("--- ChatReplyNode End ---")
    return {"chatReply": {"message": message}}
