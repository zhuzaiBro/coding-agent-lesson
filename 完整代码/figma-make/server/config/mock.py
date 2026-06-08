"""
全局 Mock 配置

控制哪些节点使用本地 mock 数据（快速），哪些调用真实 LLM（慢，但有创造性）。
支持三层粒度，优先级从高到低：

  nodes（节点级）  > phases（阶段级）> global（全局）> 默认值（True = 全 mock）

阶段与节点对照：
  planning  - analysisNode / intentNode / capabilityNode / uiNode / componentNode / structureNode / dependencyNode
  foundation - typeNode / utilsNode / mockDataNode
  logic      - serviceNode / hooksNode
  view       - componentSubgraph / pageSubgraph / layoutNode / styleGenNode
  assembly   - appGenNode

常用预设（见文件末尾 MOCK_PRESETS）：
  allMock       - 全部 Mock，用于 UI 调试
  allReal       - 全部真实 LLM，完整测试
  planningMock  - 仅规划阶段 Mock，其余真实（调试代码生成）
"""
from typing import Literal, Optional

NodeName = Literal[
    "analysisNode", "intentNode", "capabilityNode", "uiNode", "componentNode",
    "structureNode", "dependencyNode", "typeNode", "utilsNode", "mockDataNode",
    "serviceNode", "hooksNode", "componentSubgraph", "pageSubgraph",
    "layoutNode", "styleGenNode", "appGenNode",
]

PhaseName = Literal["planning", "foundation", "logic", "view", "assembly"]

PHASE_NODES: dict[str, list[str]] = {
    "planning": [
        "analysisNode", "intentNode", "capabilityNode", "uiNode",
        "componentNode", "structureNode", "dependencyNode",
    ],
    "foundation": ["typeNode", "utilsNode", "mockDataNode"],
    "logic": ["serviceNode", "hooksNode"],
    "view": ["componentSubgraph", "pageSubgraph", "layoutNode", "styleGenNode"],
    "assembly": ["appGenNode"],
}

PHASE_METADATA: dict[str, dict] = {
    "planning": {"title": "规划阶段", "order": 1},
    "foundation": {"title": "基础建设", "order": 2},
    "logic": {"title": "逻辑构建", "order": 3},
    "view": {"title": "视图构建", "order": 4},
    "assembly": {"title": "应用组装", "order": 5},
}

ALL_NODES: list[str] = [node for nodes in PHASE_NODES.values() for node in nodes]


class MockConfig:
    def __init__(
        self,
        global_: Optional[bool] = None,
        phases: Optional[dict[str, bool]] = None,
        nodes: Optional[dict[str, bool]] = None,
    ):
        self.global_ = global_
        self.phases = phases or {}
        self.nodes = nodes or {}

    def to_dict(self) -> dict:
        d: dict = {}
        if self.global_ is not None:
            d["global"] = self.global_
        if self.phases:
            d["phases"] = self.phases
        if self.nodes:
            d["nodes"] = self.nodes
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "MockConfig":
        return cls(
            global_=data.get("global"),
            phases=data.get("phases", {}),
            nodes=data.get("nodes", {}),
        )


def get_phase_by_node(node_name: str) -> Optional[str]:
    for phase, nodes in PHASE_NODES.items():
        if node_name in nodes:
            return phase
    return None


def resolve_mock_config(config: "MockConfig | dict") -> dict[str, bool]:
    """Resolve layered MockConfig to flat dict[node_name, bool].
    Priority: nodes > phases > global > default(True)
    """
    if isinstance(config, dict):
        config = MockConfig.from_dict(config)

    result: dict[str, bool] = {}
    for node_name in ALL_NODES:
        # 1. Node-level (highest priority)
        if node_name in config.nodes:
            result[node_name] = config.nodes[node_name]
            continue
        # 2. Phase-level
        if config.phases:
            phase = get_phase_by_node(node_name)
            if phase and phase in config.phases:
                result[node_name] = config.phases[phase]
                continue
        # 3. Global
        if config.global_ is not None:
            result[node_name] = config.global_
            continue
        # 4. Default: True (mock)
        result[node_name] = True

    return result


# Presets
MOCK_PRESETS = {
    "allMock": MockConfig(global_=True),
    "allReal": MockConfig(global_=False),
    "planningMock": MockConfig(global_=False, phases={"planning": True}),
    "foundationMock": MockConfig(global_=False, phases={"planning": True, "foundation": True}),
    "viewReal": MockConfig(global_=True, phases={"view": False}),
    "assemblyReal": MockConfig(global_=True, phases={"assembly": False}),
}

DEFAULT_MOCK_PRESET: MockConfig = MOCK_PRESETS["allReal"]
