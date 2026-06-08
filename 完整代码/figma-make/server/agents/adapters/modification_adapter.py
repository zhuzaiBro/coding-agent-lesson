"""
Modification request route adapter.
"""
from agents.adapters.route_helpers import is_modification_request


class ModificationRouteAdapter:
    name = "modification-route"
    priority = 90

    def can_handle(self, context: dict) -> bool:
        return is_modification_request(
            context.get("messages", []),
            context=context,
        )

    async def adapt(self, context: dict) -> dict:
        print("[RouteAdapter] Matched: modification-route")
        existing = context.get("existingFiles") or context.get("files")
        return {
            "flow": "modification",
            "input": {
                "messages": context.get("messages", []),
                "mockConfig": context.get("mockConfig", {}),
                "existingFiles": existing if isinstance(existing, dict) else None,
            },
            "meta": {"routeType": "modification"},
        }


modification_route_adapter = ModificationRouteAdapter()
