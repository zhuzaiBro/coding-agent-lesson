"""
聊天入口路由适配器注册表

职责：
1. 管理各适配器的优先级顺序
2. 按优先级执行首次匹配（first-match），将请求分流到 figma 或 traditional 流程

适配器优先级（数字越大越先匹配）：
  figma-route        100 — 消息含 Figma URL
  modification-route  90 — 请求带已有 files，或修改关键词（走 modification 轻量图）
  image-route         80 — 消息含图片附件
  prompt-route        70 — 消息含纯文本描述
  traditional-route   10 — 兜底，始终匹配
"""
from typing import Any, Dict

from agents.adapters.figma_adapter import figma_route_adapter
from agents.adapters.image_adapter import image_route_adapter
from agents.adapters.modification_adapter import modification_route_adapter
from agents.adapters.prompt_adapter import prompt_route_adapter


class FallbackRouteAdapter:
    name = "traditional-route"
    priority = 10

    def can_handle(self, context: dict) -> bool:
        return True

    async def adapt(self, context: dict) -> dict:
        return {
            "flow": "traditional",
            "input": {
                "messages": context.get("messages", []),
                "mockConfig": context.get("mockConfig", {}),
            },
            "meta": {"routeType": "fallback"},
        }


_fallback_adapter = FallbackRouteAdapter()

# All adapters sorted by priority (descending)
_ROUTE_ADAPTERS = sorted(
    [
        figma_route_adapter,
        modification_route_adapter,
        image_route_adapter,
        prompt_route_adapter,
        _fallback_adapter,
    ],
    key=lambda a: a.priority,
    reverse=True,
)


async def resolve_route_adapter(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve which adapter to use and adapt the context.

    Uses first-match strategy based on priority order.
    """
    for adapter in _ROUTE_ADAPTERS:
        if adapter.can_handle(context):
            print(
                f"[RouteRegistry] Selected adapter: {adapter.name} (priority={adapter.priority})"
            )
            return await adapter.adapt(context)

    # Should never reach here since fallback always matches
    print("[RouteRegistry] Selected adapter: traditional-route (fallback)")
    return await _fallback_adapter.adapt(context)
