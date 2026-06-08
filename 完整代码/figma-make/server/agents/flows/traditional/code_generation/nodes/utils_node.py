"""step8: Utils generation node."""
from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.code_generation.prompts.utils_prompts import UTILS_SYSTEM_PROMPT
from agents.flows.traditional.code_generation.schemas.utils_schema import UtilsGenerationResult
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry


async def utils_node(state: dict) -> dict:
    """Generate utility function files."""
    mock_result = await try_execute_mock(state, "utilsNode", "utilsResult.json", "utils")
    if mock_result:
        return mock_result

    print("--- UtilsNode Start ---")

    structured_model = get_structured_model(UtilsGenerationResult)

    intent = state.get("intent") or {}
    product = intent.get("product") or {}
    product_name = product.get("name", "the application")

    human_msg = f"""Generate utility functions for '{product_name}'.

Include at minimum:
1. /lib/utils.ts with cn() helper (clsx + tailwind-merge)
2. Any additional utility functions needed (formatDate, formatCurrency, etc.)

Keep utilities focused and reusable."""

    prompt = [
        SystemMessage(content=UTILS_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[UtilsNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = normalize_llm_result(result_dict) or {}
    files = result_dict.get("files") or []
    print(f"--- UtilsNode End ({len(files)} files) ---")

    return {"utils": result_dict}
