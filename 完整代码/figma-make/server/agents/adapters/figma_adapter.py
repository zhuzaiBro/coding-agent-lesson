"""
Figma 路由适配器（优先级 100，最高）。

匹配条件：消息文本中含 Figma 设计稿 URL。
输出 flow="figma"，将 figmaUrl 传入 figma_graph 入口。
"""
from agents.shared.utils.figma_url import extract_figma_url


class FigmaRouteAdapter:
    name = "figma-route"
    priority = 100

    def can_handle(self, context: dict) -> bool:
        return bool(extract_figma_url(context.get("messages", [])))

    async def adapt(self, context: dict) -> dict:
        messages = context.get("messages", [])
        figma_url = extract_figma_url(messages)
        print(f"[RouteAdapter] Matched: figma-route, url={figma_url}")
        return {
            "flow": "figma",
            "input": {"messages": messages, "figmaUrl": figma_url},
            "meta": {"figmaUrl": figma_url},
        }


figma_route_adapter = FigmaRouteAdapter()
