"""
Image request route adapter.
"""
from agents.adapters.route_helpers import has_image_attachment


class ImageRouteAdapter:
    name = "image-route"
    priority = 80

    def can_handle(self, context: dict) -> bool:
        return has_image_attachment(context.get("messages", []))

    async def adapt(self, context: dict) -> dict:
        print("[RouteAdapter] Matched: image-route")
        return {
            "flow": "traditional",
            "input": {
                "messages": context.get("messages", []),
                "mockConfig": context.get("mockConfig", {}),
            },
            "meta": {"routeType": "image"},
        }


image_route_adapter = ImageRouteAdapter()
