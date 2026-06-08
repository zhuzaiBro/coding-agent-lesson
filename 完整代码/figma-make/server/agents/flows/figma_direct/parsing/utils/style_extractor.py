"""
Style extractor utilities.

Extracts layout positioning info from Tailwind class names and inline styles.
Converts JsxElement dicts to LayoutBlock dicts with coordinate information.
"""
import re
from typing import Any, Dict, List, Optional

# Decorative asset pattern: Vector, Group, MaskGroup, Ellipse
_DECORATIVE_PATTERN = re.compile(r"^img(Vector|Group|MaskGroup|Ellipse)\d*$")


def extract_texts(raw_jsx: str) -> List[str]:
    """Extract all text content from JSX code."""
    texts = []
    for m in re.finditer(r">([^<>{]+)<", raw_jsx):
        text = m.group(1).strip()
        if text and not text.isspace():
            texts.append(text)
    # Deduplicate preserving order
    return list(dict.fromkeys(texts))


def extract_used_assets(raw_jsx: str) -> List[str]:
    """Extract referenced image variable names from JSX code."""
    assets = []
    for m in re.finditer(r"\{(img[A-Za-z0-9][a-zA-Z0-9]*)\}", raw_jsx):
        assets.append(m.group(1))
    return list(dict.fromkeys(assets))


def _parse_tailwind_layout(class_name: Optional[str]) -> Dict[str, float]:
    """Extract positioning values from Tailwind class names."""
    result = {"top": 0.0, "left": 0.0, "width": 0.0, "height": 0.0}
    if not class_name:
        return result

    top_m = re.search(r"\btop-\[(-?\d+(?:\.\d+)?)px\]", class_name)
    if top_m:
        result["top"] = float(top_m.group(1))

    left_m = re.search(r"\bleft-\[(-?\d+(?:\.\d+)?)px\]", class_name)
    if left_m:
        result["left"] = float(left_m.group(1))

    width_m = re.search(r"\bw-\[(-?\d+(?:\.\d+)?)px\]", class_name)
    if width_m:
        result["width"] = float(width_m.group(1))

    height_m = re.search(r"\bh-\[(-?\d+(?:\.\d+)?)px\]", class_name)
    if height_m:
        result["height"] = float(height_m.group(1))

    return result


def _parse_inline_style_layout(inline_style: Optional[str]) -> Dict[str, float]:
    """Extract positioning values from inline style string."""
    result = {"top": 0.0, "left": 0.0, "width": 0.0, "height": 0.0}
    if not inline_style:
        return result

    pairs = re.findall(r"(\w+)\s*:\s*['\"]?(-?\d+(?:\.\d+)?(?:px)?)['\"]?", inline_style)
    for key, value in pairs:
        num_str = value.replace("px", "")
        try:
            num = float(num_str)
        except ValueError:
            continue

        if key in result:
            result[key] = num

    return result


def _detect_background(class_name: Optional[str], width: float, height: float) -> bool:
    """Detect if element is a full-page background element."""
    if width >= 1200 and height >= 500:
        return True

    if class_name:
        if re.search(r"\b(w-full|w-screen|w-\[100%\]|w-\[100vw\])\b", class_name) and height >= 500:
            return True

    return False


def _detect_decorative(texts: List[str], used_assets: List[str]) -> bool:
    """Detect purely decorative elements (no text, only decorative assets)."""
    if texts:
        return False
    if not used_assets:
        return False
    return all(_DECORATIVE_PATTERN.match(a) for a in used_assets)


def extract_layout_block(elem: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Convert a JsxElement to a LayoutBlock with extracted layout info."""
    class_name = elem.get("className")
    inline_style = elem.get("inlineStyle")

    tw = _parse_tailwind_layout(class_name)
    inline = _parse_inline_style_layout(inline_style)

    top = tw["top"] if tw["top"] != 0 else inline["top"]
    left = tw["left"] if tw["left"] != 0 else inline["left"]
    width = tw["width"] if tw["width"] != 0 else inline["width"]
    height = tw["height"] if tw["height"] != 0 else inline["height"]

    is_background = _detect_background(class_name, width, height)

    raw_jsx = elem.get("rawJsx", "")
    texts = extract_texts(raw_jsx)
    used_assets = extract_used_assets(raw_jsx)

    if not is_background:
        is_background = _detect_decorative(texts, used_assets)

    return {
        "index": index,
        "rawJsx": raw_jsx,
        "top": top,
        "left": left,
        "width": width,
        "height": height,
        "texts": texts,
        "usedAssets": used_assets,
        "childrenCount": elem.get("childrenCount", 0),
        "isBackground": is_background,
        "nodeId": elem.get("nodeId"),
        "dataName": elem.get("dataName"),
    }
