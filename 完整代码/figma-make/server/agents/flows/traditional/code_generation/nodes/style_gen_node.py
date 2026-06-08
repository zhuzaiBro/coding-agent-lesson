"""Global style generation node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.code_generation.prompts.style_gen_prompts import STYLE_GEN_SYSTEM_PROMPT
from agents.flows.traditional.code_generation.schemas.style_gen_schema import StyleGenResult
from agents.utils.code_normalizer import normalize_llm_result
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry
from agents.utils.state_helpers import as_dict


async def style_gen_node(state: dict) -> dict:
    """Generate global CSS styles."""
    mock_result = await try_execute_mock(state, "styleGenNode", "styleGenResult.json", "styles")
    if mock_result:
        return mock_result

    print("--- StyleGenNode Start ---")

    structured_model = get_structured_model(StyleGenResult)

    ui = as_dict(state.get("ui"))
    analysis = as_dict(state.get("analysis"))

    theme_strategy = ui.get("themeStrategy") or "Modern, clean design"
    design_analysis = analysis.get("designAnalysis") or ""

    human_msg = f"""Generate global CSS styles for this application:

Theme Strategy: {theme_strategy}
Design Analysis: {design_analysis or 'Standard modern web application'}

Create a styles.css file with CSS variables, custom animations, and complementary styles for Tailwind CSS."""

    prompt = [
        SystemMessage(content=STYLE_GEN_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[StyleGenNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = normalize_llm_result(result_dict)
    print("--- StyleGenNode End ---")

    return {"styles": result_dict}
