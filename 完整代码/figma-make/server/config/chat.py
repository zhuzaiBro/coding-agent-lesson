# 节点名 → SSE 事件映射表
#
# chat 路由每收到一个 LangGraph 节点的输出 chunk，就按此表：
#   type：推送给前端的 SSE 事件类型（前端按 type 区分进度步骤）
#   key ：从节点输出的 State 字典里取哪个字段作为 payload
#
# serviceNode 输出 state["service"]，SSE type 为 "service"。
NODE_HANDLERS: dict[str, dict[str, str]] = {
    # ==================== Traditional 流程节点 ====================
    "analysisNode": {"type": "analysis", "key": "analysis"},
    "inquiryNode": {"type": "inquiry", "key": "inquiry"},
    "chatReplyNode": {"type": "chatReply", "key": "chatReply"},
    "intentNode": {"type": "intent", "key": "intent"},
    "capabilityNode": {"type": "capabilities", "key": "capabilities"},
    "uiNode": {"type": "ui", "key": "ui"},
    "componentNode": {"type": "components", "key": "components"},
    "structureNode": {"type": "structure", "key": "structure"},
    "dependencyNode": {"type": "dependency", "key": "dependency"},
    "supabaseSubgraph": {"type": "supabase", "key": "supabase"},
    "typeNode": {"type": "types", "key": "types"},
    "utilsNode": {"type": "utils", "key": "utils"},
    "mockDataNode": {"type": "mockData", "key": "mockData"},
    "serviceNode": {"type": "service", "key": "service"},
    "hooksNode": {"type": "hooks", "key": "hooks"},
    "componentSubgraph": {"type": "componentsCode", "key": "componentsCode"},
    "pageSubgraph": {"type": "pagesCode", "key": "pagesCode"},
    "layoutNode": {"type": "layouts", "key": "layouts"},
    "styleGenNode": {"type": "styles", "key": "styles"},
    "appGenNode": {"type": "app", "key": "app"},
    "assembleNode": {"type": "files", "key": "files"},
    "postProcessNode": {"type": "files", "key": "files"},        # 与 assembleNode 同 type，前端覆盖更新
    "compileCheckNode": {"type": "files", "key": "files"},       # 编译检查后的文件集
    "debugFixNode": {"type": "files", "key": "files"},           # 编译失败 LLM 修复
    "figmaDebugFixNode": {"type": "figmaAssembly", "key": "files"},

    # ==================== Modification 流程（在已生成应用上迭代） ====================
    "loadExistingNode": {"type": "modification", "key": "modification"},
    "userModifyNode": {"type": "files", "key": "files"},

    # ==================== Figma 直连流程节点 ====================
    "figmaInputNode": {"type": "figmaRawCode", "key": "rawCode"},
    "imageDownloadNode": {"type": "figmaImageProcessed", "key": "rawCode"},
    "astParserNode": {"type": "figmaAstParsed", "key": "astParserResult"},
    "blockExtractNode": {"type": "figmaBlockExtract", "key": "blockExtractResult"},
    "geometryGroupNode": {"type": "figmaGeometryGroup", "key": "geometryGroupResult"},
    "sectionNamingNode": {"type": "figmaSectionNaming", "key": "sectionNamingResult"},
    "componentGenNode": {"type": "figmaComponentGen", "key": "generatedFiles"},
    "assemblyNode": {"type": "figmaAssembly", "key": "files"},
    "figmaPostProcessNode": {"type": "figmaAssembly", "key": "files"},
    "figmaCompileCheckNode": {"type": "figmaAssembly", "key": "files"},
}
