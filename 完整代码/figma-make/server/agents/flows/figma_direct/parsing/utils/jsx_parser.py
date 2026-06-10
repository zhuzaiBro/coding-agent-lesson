"""
JSX/TSX 解析工具（基于正则）。

TypeScript Babel 解析器的 Python 等价实现。
通过正则提取：
1. 主入口组件（export default）
2. 主组件 return 块中的顶层 JSX 元素
3. 全局图片资源变量（const imgXxx = "https://..."）
4. 辅助组件（非 default export 的函数组件）
"""
import re
from typing import Any, Dict, List, Optional, Tuple


def _extract_global_assets(code: str) -> List[Dict[str, str]]:
    """提取全局图片资源变量声明。"""
    assets = []
    pattern = r"""(?:export\s+)?const\s+(img[A-Za-z0-9]\w*)\s*=\s*["']([^"']+)["']\s*;?"""
    for m in re.finditer(pattern, code):
        var_name, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://")):
            assets.append({"variableName": var_name, "url": url})
    return assets


def _find_default_export_name(code: str) -> Optional[str]:
    """查找 default export 的组件名。"""
    # export default function ComponentName
    m = re.search(r"export\s+default\s+function\s+(\w+)", code)
    if m:
        return m.group(1)

    # export default ComponentName（标识符形式）
    m = re.search(r"export\s+default\s+(\w+)\s*;", code)
    if m:
        name = m.group(1)
        if name not in ("class", "function", "const", "let", "var"):
            return name

    return None


def _find_matching_brace(code: str, start: int) -> int:
    """找到 start 处开括号对应的闭括号位置。"""
    depth = 0
    i = start
    while i < len(code):
        c = code[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _find_component_body(code: str, component_name: str) -> Optional[str]:
    """提取具名组件函数体。"""
    # 函数声明: function Name(...) {
    pattern = rf"function\s+{re.escape(component_name)}\s*\([^)]*\)\s*\{{"
    m = re.search(pattern, code)
    if m:
        brace_start = m.end() - 1
        brace_end = _find_matching_brace(code, brace_start)
        if brace_end > 0:
            return code[brace_start:brace_end + 1]

    # 箭头函数: const Name = (...) => {
    pattern = rf"const\s+{re.escape(component_name)}\s*=\s*(?:\([^)]*\)|\w+)\s*=>\s*\{{"
    m = re.search(pattern, code)
    if m:
        brace_start = m.end() - 1
        brace_end = _find_matching_brace(code, brace_start)
        if brace_end > 0:
            return code[brace_start:brace_end + 1]

    return None


def _extract_top_level_jsx_elements(return_block: str, lines: List[str], code_offset: int) -> List[Dict[str, Any]]:
    """
    从 return 块中提取顶层 JSX 元素。
    使用正则匹配 return 语句的直接子元素。
    """
    elements = []

    # 查找 return ( ... ) 块
    return_match = re.search(r"\breturn\s*\(", return_block)
    if not return_match:
        # 尝试无括号的 return
        return_match = re.search(r"\breturn\s+<", return_block)
        if not return_match:
            return elements

    # 启发式：在 return(...) 内第一层嵌套中查找顶层 JSX 开标签
    return_start = return_match.start()
    remaining = return_block[return_start:]

    # 基于深度的 JSX 元素边界扫描
    depth = 0
    i = 0
    in_return_parens = False
    elements_raw = []

    jsx_pattern = re.compile(r"<([A-Za-z][A-Za-z0-9]*|[a-z]+)[\s>]")

    # 简化策略：匹配看起来像完整 JSX 元素的块
    block_pattern = re.compile(r"\{(/\*.*?\*/|[^{}]*)\}", re.DOTALL)

    child_pattern = re.compile(
        r"(<(?:[A-Za-z][A-Za-z0-9.]*|[a-z]+)(?:\s[^>]*)?>(?:[\s\S]*?)</[A-Za-z][A-Za-z0-9.]*>|"
        r"<(?:[A-Za-z][A-Za-z0-9.]*|[a-z]+)(?:\s[^>]*)?\s*/>)"
    )

    idx = 0
    for m in re.finditer(
        r"(<(?:div|section|header|footer|nav|main|article|aside|span|p|h[1-6]|img|button|a|ul|ol|li|form|input|[A-Z][A-Za-z0-9]*)"
        r"[\s\S]*?(?:</[A-Za-z][A-Za-z0-9]*>|/>))",
        return_block,
    ):
        raw_jsx = m.group(0)
        # 跳过过短片段（闭合标签等）
        if len(raw_jsx) < 5:
            continue

        # 估算源码行号
        start_pos = m.start()
        before = return_block[:start_pos]
        start_line = before.count("\n") + 1

        # 提取 className
        class_m = re.search(r'className=["\']([^"\']*)["\']', raw_jsx)
        class_name = class_m.group(1) if class_m else None

        # 提取内联 style
        style_m = re.search(r'style=\{(\{[^}]*\})\}', raw_jsx)
        inline_style = style_m.group(1) if style_m else None

        # 提取 data-node-id
        node_id_m = re.search(r'data-node-id=["\']([^"\']*)["\']', raw_jsx)
        node_id = node_id_m.group(1) if node_id_m else None

        # 提取 data-name
        data_name_m = re.search(r'data-name=["\']([^"\']*)["\']', raw_jsx)
        data_name = data_name_m.group(1) if data_name_m else None

        # 子元素数量（启发式）
        children_count = len(re.findall(r"<[A-Za-z][A-Za-z0-9]*[\s>]", raw_jsx)) - 1

        elements.append({
            "index": idx,
            "rawJsx": raw_jsx,
            "className": class_name,
            "inlineStyle": inline_style,
            "nodeId": node_id,
            "dataName": data_name,
            "childrenCount": max(0, children_count),
            "loc": {"startLine": start_line, "endLine": start_line + raw_jsx.count("\n")},
        })
        idx += 1

        # 仅取顶层元素（最多 30 个）
        if idx >= 30:
            break

    return elements


def _extract_helper_components(code: str, entry_name: str) -> List[Dict[str, Any]]:
    """提取辅助组件（非 default export 的函数组件）。"""
    helpers = []
    lines = code.split("\n")

    # 函数声明: function ComponentName(...)
    for m in re.finditer(r"(?:^|\n)(function\s+([A-Z]\w*)\s*\([^)]*\)\s*\{)", code):
        name = m.group(2)
        if name == entry_name:
            continue

        start_pos = m.start(1) if m.start(1) > 0 else m.start()
        brace_pos = code.index("{", start_pos + m.start(1) - m.start())
        end_pos = _find_matching_brace(code, code.index("{", start_pos))
        if end_pos < 0:
            continue

        raw_code = code[start_pos:end_pos + 1]

        # 判断是否像 React 组件（含 JSX 返回）
        if "<" not in raw_code:
            continue

        start_line = code[:start_pos].count("\n") + 1
        end_line = code[:end_pos].count("\n") + 1

        helpers.append({
            "name": name,
            "rawCode": raw_code,
            "loc": {"startLine": start_line, "endLine": end_line},
        })

    return helpers


def parse_tsx_code(raw_code: str) -> Dict[str, Any]:
    """
    解析 TSX 源码并提取结构信息。

    返回与 AstParserOutput 兼容的字典：
    {
        entryComponentName: str,
        jsxElements: List[JsxElement],
        globalAssets: List[GlobalAsset],
        helperComponents: List[HelperComponent],
    }
    """
    lines = raw_code.split("\n")

    # 1. 查找 default export 组件名
    entry_name = _find_default_export_name(raw_code) or "App"

    # 2. 提取全局图片资源
    global_assets = _extract_global_assets(raw_code)

    # 3. 提取辅助组件
    helper_components = _extract_helper_components(raw_code, entry_name)

    # 4. 从主组件中提取顶层 JSX 元素
    component_body = _find_component_body(raw_code, entry_name)
    jsx_elements = []
    if component_body:
        jsx_elements = _extract_top_level_jsx_elements(component_body, lines, 0)

    # 若从函数体未找到元素，尝试更简单的兜底策略
    if not jsx_elements:
        # 查找带绝对/相对定位的顶层 div（Figma 常见模式）
        for i, m in enumerate(re.finditer(
            r'(<(?:div|section)\s+[^>]*className=["\'][^"\']*(?:absolute|relative)[^"\']*["\'][^>]*>[\s\S]{10,}?(?:</div>|/>))',
            raw_code[:5000],  # 仅扫描前 5000 字符以提升性能
        )):
            if i >= 20:
                break
            raw_jsx = m.group(1)
            class_m = re.search(r'className=["\']([^"\']*)["\']', raw_jsx)
            jsx_elements.append({
                "index": i,
                "rawJsx": raw_jsx,
                "className": class_m.group(1) if class_m else None,
                "inlineStyle": None,
                "nodeId": None,
                "dataName": None,
                "childrenCount": 0,
                "loc": {"startLine": 1, "endLine": 1},
            })

    return {
        "entryComponentName": entry_name,
        "jsxElements": jsx_elements,
        "globalAssets": global_assets,
        "helperComponents": helper_components,
    }
