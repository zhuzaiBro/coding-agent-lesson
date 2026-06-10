"""
Y 轴几何聚类算法（确定性，无 AI）

将 LayoutBlock 列表按 Y 轴坐标（top 值）分组为语义上有意义的 Section。
每个 Section 对应设计稿中的一个独立区域（如 Header / Hero / Features / Footer）。

算法流程：
1. 分离背景元素和普通元素（背景不参与间距计算，避免干扰聚类）
2. 按 top 值升序排序
3. 计算相邻元素之间的间距（gap）
4. 自适应阈值 = median(gaps) × 1.5（避免硬编码阈值在不同尺寸设计稿失效）
5. gap > 阈值 → 新 Section 起始边界
6. 将背景元素分配到与其 Y 范围重叠最多的 Section

关键常数说明：
  MIN_THRESHOLD = 80   — 防止过度分割（间距过小的相邻元素会被合并）
  MAX_THRESHOLD = 500  — 防止分割不足（超大空白仍强制切割）
"""
import statistics
from typing import Any, Dict, List

MIN_THRESHOLD = 80      # 最小聚类阈值，低于此值不切割
MAX_THRESHOLD = 500     # 最大聚类阈值，超过此值强制切割
MIN_SECTIONS = 2
MAX_SECTIONS = 15
MIN_SECTION_HEIGHT = 100  # 高度低于此值的 Section 会被合并


def cluster_by_geometry(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按 Y 轴几何位置将 LayoutBlock 聚类为 Section。"""
    if not blocks:
        return {"sections": [], "threshold": 0}

    # 分离背景元素与普通元素
    normal_blocks = [b for b in blocks if not b.get("isBackground", False)]
    background_blocks = [b for b in blocks if b.get("isBackground", False)]

    if not normal_blocks:
        return {
            "sections": [_build_section(0, blocks, background_blocks)],
            "threshold": 0,
        }

    # 按 top 升序排序
    sorted_blocks = sorted(normal_blocks, key=lambda b: b.get("top", 0))

    if len(sorted_blocks) == 1:
        return {
            "sections": [_build_section(0, sorted_blocks, _assign_backgrounds(background_blocks, sorted_blocks))],
            "threshold": 0,
        }

    # 计算相邻元素间距
    gaps = []
    for i in range(1, len(sorted_blocks)):
        gap = sorted_blocks[i].get("top", 0) - sorted_blocks[i - 1].get("top", 0)
        gaps.append(gap)

    # 计算自适应阈值
    threshold = _compute_adaptive_threshold(gaps)

    # 按阈值切分 Section
    groups: List[List[Dict]] = []
    current_group = [sorted_blocks[0]]

    for i in range(1, len(sorted_blocks)):
        gap = sorted_blocks[i].get("top", 0) - sorted_blocks[i - 1].get("top", 0)
        if gap > threshold:
            groups.append(current_group)
            current_group = [sorted_blocks[i]]
        else:
            current_group.append(sorted_blocks[i])
    groups.append(current_group)

    # 后处理：合并过短的 Section
    groups = _merge_short_sections(groups)
    groups = _merge_excess_sections(groups)

    # 构建 Section 并分配背景元素
    sections = []
    for i, group in enumerate(groups):
        bg = _assign_backgrounds(background_blocks, group)
        sections.append(_build_section(i, group, bg))

    return {"sections": sections, "threshold": threshold}


def _compute_adaptive_threshold(gaps: List[float]) -> float:
    """计算自适应阈值 = median(gaps) × 1.5，限制在 [MIN, MAX] 范围内。"""
    if not gaps:
        return MIN_THRESHOLD

    sorted_gaps = sorted(gaps)
    n = len(sorted_gaps)
    if n % 2 == 0:
        median = (sorted_gaps[n // 2 - 1] + sorted_gaps[n // 2]) / 2
    else:
        median = sorted_gaps[n // 2]

    threshold = median * 1.5
    return max(MIN_THRESHOLD, min(MAX_THRESHOLD, threshold))


def _merge_short_sections(groups: List[List[Dict]]) -> List[List[Dict]]:
    """合并高度低于 MIN_SECTION_HEIGHT 的 Section。"""
    if len(groups) <= MIN_SECTIONS:
        return groups

    result = list(groups)
    i = 0
    while i < len(result) and len(result) > MIN_SECTIONS:
        group = result[i]
        tops = [b.get("top", 0) for b in group]
        bottoms = [b.get("top", 0) + b.get("height", 0) for b in group]
        section_height = max(bottoms) - min(tops) if group else 0

        if section_height < MIN_SECTION_HEIGHT and len(group) <= 2:
            if i < len(result) - 1:
                result[i + 1] = group + result[i + 1]
            elif i > 0:
                result[i - 1] = result[i - 1] + group
            else:
                i += 1
                continue
            result.pop(i)
        else:
            i += 1

    return result


def _merge_excess_sections(groups: List[List[Dict]]) -> List[List[Dict]]:
    """Section 数量超过 MAX_SECTIONS 时合并相邻分组。"""
    if len(groups) <= MAX_SECTIONS:
        return groups

    result = list(groups)

    while len(result) > MAX_SECTIONS:
        # 找到间距最小的相邻 Section 进行合并
        min_gap = float("inf")
        merge_idx = 0

        for i in range(len(result) - 1):
            last = result[i][-1].get("top", 0) if result[i] else 0
            first = result[i + 1][0].get("top", 0) if result[i + 1] else 0
            gap = first - last
            if gap < min_gap:
                min_gap = gap
                merge_idx = i

        result[merge_idx] = result[merge_idx] + result[merge_idx + 1]
        result.pop(merge_idx + 1)

    return result


def _assign_backgrounds(bg_blocks: List[Dict], section_blocks: List[Dict]) -> List[Dict]:
    """将 Y 范围与 Section 重叠的背景块分配到该 Section。"""
    if not bg_blocks or not section_blocks:
        return []

    section_top = min(b.get("top", 0) for b in section_blocks)
    section_bottom = max(b.get("top", 0) for b in section_blocks)

    result = []
    for bg in bg_blocks:
        bg_top = bg.get("top", 0)
        bg_bottom = bg_top + bg.get("height", 0)
        if bg_top <= section_bottom and bg_bottom >= section_top:
            result.append(bg)
    return result


def _build_section(
    index: int,
    blocks: List[Dict],
    background_blocks: List[Dict],
) -> Dict[str, Any]:
    """由布局块列表构建 Section 字典。"""
    tops = [b.get("top", 0) for b in blocks]
    top_min = min(tops) if tops else 0
    top_max = max(tops) if tops else 0

    all_texts_raw = []
    for b in blocks:
        all_texts_raw.extend(b.get("texts", []))
    all_texts = list(dict.fromkeys(all_texts_raw))  # 去重并保持顺序

    content_assets = []
    for b in blocks:
        content_assets.extend(b.get("usedAssets", []))
    bg_assets = []
    for b in background_blocks:
        bg_assets.extend(b.get("usedAssets", []))
    all_assets = list(dict.fromkeys(content_assets + bg_assets))

    return {
        "index": index,
        "blocks": blocks,
        "topRange": {"min": top_min, "max": top_max},
        "allTexts": all_texts,
        "allAssets": all_assets,
        "totalBlocks": len(blocks),
        "backgroundBlocks": background_blocks,
    }
