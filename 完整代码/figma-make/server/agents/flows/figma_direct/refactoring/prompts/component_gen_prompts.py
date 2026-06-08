"""Component generation prompts for Figma direct flow."""
from typing import Any, Dict, List, Optional


def get_component_gen_system_prompt() -> str:
    return """You are a senior React + TypeScript frontend engineer. Your task is to refactor raw JSX code exported from Figma (absolute-positioned) into a high-quality, maintainable, responsive React component.

## Core Background

The raw code comes from Figma MCP export with these characteristics:
- All elements use `position: absolute` + fixed pixel coordinates (e.g. `top-[3759px] left-[240px]`)
- Coordinates are global canvas coordinates relative to Figma canvas origin
- Contains Figma internal attributes (data-node-id, data-name)
- Fonts use Figma format (e.g. MiSans:Medium)
- Images use extreme percentage overflow positioning

You need to **understand the visual intent** of the raw code, then re-implement with modern frontend best practices.

## Refactoring Rules (Critical)

### 1. Layout System (Highest Priority)
- **Remove ALL global/absolute coordinates**: Delete `top-[Npx]`, `left-[Npx]`, etc.
- **Outer container**: Use `relative` + `w-full`, never use `absolute`
- **Content centering**: Use `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`
- **Internal layout** (choose based on element relationships):
  - Horizontal: `flex items-center gap-N` or `grid grid-cols-N gap-N`
  - Vertical: `flex flex-col gap-N`
  - Cards/grid: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6`

### 2. Forbidden Values (Figma canvas sizes)
- `w-[1920px]`, `h-[1080px]`, large fixed heights
- Use `w-full` with `max-w-7xl mx-auto` instead

### 3. Image Handling
- Remove Figma-style extreme image cropping
- Logos/icons: `object-contain`
- Banner/background: `object-cover w-full h-full`
- Avatars: `object-cover rounded-full`

### 4. Cleanup
- Remove all data-node-id and data-name attributes
- Replace Figma font names with system fonts or standard fonts
- Remove Figma-specific mask/filter effects

### 5. Code Quality
- Export as default
- Include TypeScript props interface
- Accept image variables as props
- Use semantic HTML elements

Output ONE component file with filePath, code, and componentName."""


def get_component_gen_human_prompt(
    component_name: str,
    description: str,
    raw_jsx: str,
    available_assets: List[Dict[str, str]],
    helper_components: Optional[List[Dict[str, Any]]] = None,
) -> str:
    assets_desc = ""
    if available_assets:
        asset_list = "\n".join(f"  - {a['variableName']}: {a['url']}" for a in available_assets[:20])
        assets_desc = f"\n\n## Available Image Assets\n{asset_list}"

    helpers_desc = ""
    if helper_components:
        helpers_desc = f"\n\n## Helper Components (include in same file if needed)\n"
        for h in helper_components:
            helpers_desc += f"### {h['name']}\n```tsx\n{h['rawCode']}\n```\n"

    return f"""## Task
Refactor the following Figma-exported JSX section into a clean React component.

## Component Info
- Name: {component_name}
- Description: {description}
- File: components/{component_name}.tsx{assets_desc}{helpers_desc}

## Raw JSX Code
```tsx
{raw_jsx}
```

Please generate a complete, self-contained React component that:
1. Removes all absolute positioning with global coordinates
2. Uses responsive Tailwind CSS layout
3. Accepts image variables as props
4. Keeps the visual design intent

Return JSON with: filePath, code, componentName."""
