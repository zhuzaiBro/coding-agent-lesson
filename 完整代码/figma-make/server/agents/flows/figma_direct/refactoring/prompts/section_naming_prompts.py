"""
Figma 直连流程 - Section 命名 Prompt。

供 section_naming_node 调用 LLM 为页面区域生成语义化组件名。
Prompt 正文保持英文，以便模型输出稳定的 PascalCase 命名。
"""
from typing import Any, Dict, List


def get_section_naming_system_prompt() -> str:
    return """You are a frontend component naming expert. Your task is to give semantically meaningful React component names to webpage sections.

Naming Rules:
1. Use PascalCase style (e.g. HeroSection, FeatureGrid, FooterNav)
2. Names should reflect the area's function or content
3. Names should be concise, usually 1-3 words
4. Avoid meaningless numbers like Section1, Section2
5. If content is unclear, name based on position (TopBanner, MiddleContent, BottomArea)
6. **Each name must be globally unique** - no two sections can share the same componentName

Common naming examples:
- Navigation: Navbar, Navigation, TopNav
- Main banner: HeroBanner, HeroSection
- Features: FeatureGrid, FeatureList, Features
- Content: ContentArea, MainContent, ArticleSection
- Cards: CardGrid, CardSection, ProductCards
- Statistics: StatsSection, NumbersSection
- Forms: ContactForm, SignupForm
- Footer: Footer, FooterNav
- Sidebar: Sidebar, SidePanel
- CTA: CTASection, CallToAction

Return JSON with a namedSections array. Each item must have: index, componentName, description, fileName."""


def get_section_naming_human_prompt(
    sections_info: List[Dict[str, Any]],
) -> str:
    sections_desc = []
    for s in sections_info:
        texts = (
            f"Text content: [{', '.join(s['allTexts'][:8])}{'...' if len(s['allTexts']) > 8 else ''}]"
            if s["allTexts"]
            else "No text content"
        )
        assets = f"Referenced images: {len(s['allAssets'])}" if s["allAssets"] else "No images"
        bg = "Has background" if s.get("hasBackground") else "No background"

        sections_desc.append(
            f"Section {s['index']}:\n"
            f"  - Elements: {s['totalBlocks']}\n"
            f"  - Y range: {s['topRange']['min']}px ~ {s['topRange']['max']}px\n"
            f"  - {texts}\n"
            f"  - {assets}\n"
            f"  - {bg}"
        )

    return f"""Please name the following {len(sections_info)} page sections.
Each section is arranged top-to-bottom by Y-axis position:

{chr(10).join(chr(10).join(parts) for parts in [desc.split(chr(10)) for desc in sections_desc])}

Please return componentName (PascalCase), description (brief), and fileName (without extension) for each section."""
