"""
Text prompt route adapter.
"""
from agents.adapters.route_helpers import has_text_prompt


class PromptRouteAdapter:
    name = "prompt-route"
    priority = 70

    def can_handle(self, context: dict) -> bool:
        return has_text_prompt(context.get("messages", []))

    async def adapt(self, context: dict) -> dict:
        print("[RouteAdapter] Matched: prompt-route")
        return {
            "flow": "traditional",
            "input": {
                "messages": context.get("messages", []),
                "mockConfig": context.get("mockConfig", {}),
            },
            "meta": {"routeType": "prompt"},
        }


prompt_route_adapter = PromptRouteAdapter()
