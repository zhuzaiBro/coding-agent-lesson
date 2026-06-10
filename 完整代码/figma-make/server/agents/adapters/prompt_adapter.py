"""
纯文本路由适配器（优先级 70）。

匹配条件：最后一条消息去掉 URL 后仍有实质文本。
输出 flow="traditional"，进入完整生成流水线。
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
