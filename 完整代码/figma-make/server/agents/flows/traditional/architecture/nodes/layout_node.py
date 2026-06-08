"""Layout generation node."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.flows.traditional.architecture.prompts.layout_prompts import LAYOUT_SYSTEM_PROMPT
from agents.flows.traditional.architecture.schemas.layout_schema import LayoutNodeOutput
from agents.utils.mock import try_execute_mock
from agents.utils.model import get_structured_model
from agents.utils.retry import with_retry
from agents.utils.state_helpers import as_dict, dict_list


async def layout_node(state: dict) -> dict:
    """Generate Layout wrapper components."""
    mock_result = await try_execute_mock(state, "layoutNode", "layoutResult.json", "layouts")
    if mock_result:
        return mock_result

    print("--- LayoutNode Start ---")

    structured_model = get_structured_model(LayoutNodeOutput)

    ui = as_dict(state.get("ui"))
    pages = dict_list(ui, "pages")

    # Determine unique layout types needed
    layout_types: dict = {}
    for page in pages:
        layout = page.get("layout") or "default"
        if layout not in layout_types:
            layout_types[layout] = []
        layout_types[layout].append(page.get("pageId") or "")

    human_msg = f"""Generate Layout components for this React + React Router application:

Pages and their layouts:
{json.dumps(layout_types, ensure_ascii=False, indent=2)}

All pages:
{json.dumps([{'pageId': p.get('pageId'), 'layout': p.get('layout'), 'route': p.get('route')} for p in pages], ensure_ascii=False, indent=2)}

Generate the minimum required Layout components. Each layout uses React Router's <Outlet /> to render child routes."""

    prompt = [
        SystemMessage(content=LAYOUT_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ]

    result = await with_retry(
        structured_model,
        prompt,
        max_retries=3,
        on_retry=lambda attempt, err: print(f"[LayoutNode] Retry {attempt}: {err}"),
    )

    result_dict = result.model_dump() if hasattr(result, "model_dump") else result
    result_dict = result_dict if isinstance(result_dict, dict) else {}
    layouts_count = len(dict_list(result_dict, "layoutsCode"))
    print(f"--- LayoutNode End ({layouts_count} layouts) ---")

    return {"layouts": result_dict}
