"""
Route adapter type definitions.
"""
from typing import Any, Dict, List, Literal, Optional
from typing_extensions import Protocol, TypedDict


class RouteAdapterContext(TypedDict):
    messages: List[Any]
    mockConfig: Dict[str, bool]


class RouteAdapterResult(TypedDict, total=False):
    flow: Literal["traditional", "figma"]
    input: Dict[str, Any]
    meta: Optional[Dict[str, Any]]


class RouteInputAdapter(Protocol):
    name: str
    priority: int

    def can_handle(self, context: RouteAdapterContext) -> bool: ...

    async def adapt(self, context: RouteAdapterContext) -> RouteAdapterResult: ...
