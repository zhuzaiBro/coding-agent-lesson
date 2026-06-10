"""
图片路由适配器（优先级 80）。

匹配条件：最后一条消息带 image 类型附件。
仍走 traditional 全流程，由 analysisNode / 视觉模型理解图片意图。
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
