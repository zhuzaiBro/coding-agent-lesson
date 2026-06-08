"""
Figma direct flow - Assembly node.

Assembles all generated section components into a Sandpack-compatible file structure.
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from agents.utils.dependency_builder import build_package_json, scan_dependencies
from agents.utils.local_package_fallbacks import add_local_package_fallbacks
from agents.utils.ui_component_fallbacks import add_missing_ui_fallbacks


def _normalize_file_path(file_path: str) -> str:
    """Normalize file path for Sandpack."""
    if not file_path.startswith("/"):
        file_path = "/" + file_path
    return file_path


def _generate_assets_file(global_assets: List[Dict[str, str]]) -> str:
    """Generate assets.ts file with all image exports."""
    lines = ["// Auto-generated asset imports from Figma design", ""]
    for asset in global_assets:
        var_name = asset.get("variableName", "")
        url = asset.get("url", "")
        if var_name and url:
            lines.append(f'export const {var_name} = "{url}";')
    return "\n".join(lines) + "\n"


def _extract_defined_assets(assets_code: str) -> Set[str]:
    """Extract all defined image variable names from assets.ts."""
    assets = set()
    for m in re.finditer(r"export const (img\w+)", assets_code):
        assets.add(m.group(1))
    return assets


def _fix_undefined_image_refs(code: str, defined_assets: Set[str], file_path: str) -> tuple:
    """Remove references to undefined image variables."""
    fixed_count = 0

    def fix_img_ref(m: re.Match) -> str:
        nonlocal fixed_count
        var_name = m.group(1)
        if var_name not in defined_assets:
            fixed_count += 1
            return '""'  # Replace with empty string
        return m.group(0)

    # Fix {imgXxx} references
    fixed = re.sub(r'\{(img\w+)\}', fix_img_ref, code)

    # Fix src={imgXxx} references
    def fix_src_ref(m: re.Match) -> str:
        nonlocal fixed_count
        var_name = m.group(1)
        if var_name not in defined_assets:
            fixed_count += 1
            return 'src=""'
        return m.group(0)

    fixed = re.sub(r'src=\{(img\w+)\}', fix_src_ref, fixed)

    return fixed, fixed_count


def _sanitize_figma_artifacts(code: str) -> str:
    """Remove Figma-specific artifacts from generated code."""
    # Remove data-node-id and data-name attributes
    code = re.sub(r'\s+data-node-id="[^"]*"', "", code)
    code = re.sub(r"\s+data-node-id=\{[^}]*\}", "", code)
    code = re.sub(r'\s+data-name="[^"]*"', "", code)

    # Remove Figma font references
    code = re.sub(r"fontFamily:\s*['\"]MiSans[^'\"]*['\"]", 'fontFamily: "system-ui, sans-serif"', code)
    code = re.sub(r'font-\[\'MiSans[^\']*\'\]', 'font-sans', code)

    return code


def _generate_app_tsx(
    generated_files: List[Dict[str, Any]],
    named_sections: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Generate App.tsx that imports and renders all section components."""
    imports = []
    components = []

    for gen_result in generated_files:
        gen_file = gen_result.get("file", {}) if isinstance(gen_result, dict) else gen_result
        file_path = gen_file.get("filePath", "")
        component_name = gen_file.get("componentName", "")

        if not file_path or not component_name:
            continue

        # Generate import path
        import_path = file_path.replace(".tsx", "").replace(".ts", "")
        if not import_path.startswith("."):
            import_path = "./" + import_path.lstrip("/")

        imports.append(f"import {component_name} from '{import_path}';")
        components.append(f"      <{component_name} />")

    imports_str = "\n".join(imports)
    components_str = "\n".join(components)

    return f"""import React from 'react';
import './styles.css';
{imports_str}

export default function App() {{
  return (
    <div className="min-h-screen">
{components_str}
    </div>
  );
}}
"""


def _get_global_styles() -> str:
    """Generate basic global CSS styles."""
    return """/* Global Styles */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  scroll-behavior: smooth;
}

body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  color: #1a1a1a;
}

img {
  max-width: 100%;
  height: auto;
}

a {
  color: inherit;
  text-decoration: none;
}

button {
  cursor: pointer;
}
"""


def _get_default_index_tsx() -> str:
    """Fallback index.tsx content."""
    return """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

const root = createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""


async def assembly_node(state: dict) -> dict:
    """Assemble all Figma components into Sandpack files."""
    print("\n" + "=" * 80)
    print("[FigmaAssemblyNode] Starting file assembly")
    print("=" * 80)

    figma_components = state.get("figmaComponents", [])
    parsed_blocks = state.get("parsedBlocks", [])
    named_sections = state.get("namedSections", [])

    if not figma_components:
        print("[FigmaAssemblyNode] No generated components found")
        return {"files": {"files": {}, "stats": {"totalFiles": 0, "categories": {}}}}

    ast_output = parsed_blocks[0] if parsed_blocks else {}
    global_assets = ast_output.get("globalAssets", [])
    helper_components = ast_output.get("helperComponents", [])

    files: Dict[str, str] = {}
    categories: Dict[str, int] = {}

    def add_file(path: str, content: str, category: str):
        files[path] = content
        categories[category] = categories.get(category, 0) + 1

    # 1. Template files
    try:
        index_content = (Path.cwd() / "templates" / "react-ts" / "index.tsx").read_text(encoding="utf-8")
        add_file("/index.tsx", index_content, "entry")
    except Exception:
        add_file("/index.tsx", _get_default_index_tsx(), "entry")

    # Read template package.json for later
    template_pkg = None
    try:
        pkg_content = (Path.cwd() / "templates" / "react-ts" / "package.json").read_text(encoding="utf-8")
        template_pkg = json.loads(pkg_content)
    except Exception:
        pass

    # 2. Generate assets.ts
    if global_assets:
        assets_code = _generate_assets_file(global_assets)
        add_file("/assets.ts", assets_code, "assets")
        print(f"[FigmaAssemblyNode] Generated /assets.ts with {len(global_assets)} assets")

    # 3. Add helper components
    for helper in helper_components:
        helper_path = f"/components/{helper.get('name', 'Helper')}.tsx"
        raw_code = helper.get("rawCode", "")
        # Wrap helper with proper exports if needed
        if "export" not in raw_code:
            raw_code = f"export default function {helper.get('name')}() {{\n  return {raw_code};\n}}"
        add_file(helper_path, raw_code, "helpers")

    # 4. Add generated section components
    for gen_result in figma_components:
        gen_file = gen_result.get("file", {}) if isinstance(gen_result, dict) else gen_result
        file_path = gen_file.get("filePath", "")
        code = gen_file.get("code", "")
        if file_path and code:
            normalized_path = _normalize_file_path(file_path)
            files[normalized_path] = code
            categories["components"] = categories.get("components", 0) + 1
            print(f"[FigmaAssemblyNode] Added: {normalized_path}")

    # 5. Generate App.tsx
    app_code = _generate_app_tsx(figma_components, named_sections)
    add_file("/App.tsx", app_code, "app")

    # 6. Generate global styles
    add_file("/styles.css", _get_global_styles(), "styles")

    # 7. Fix undefined image references
    defined_assets = _extract_defined_assets(files.get("/assets.ts", ""))
    total_fixed = 0
    for fp, code in list(files.items()):
        if fp.startswith("/components/") and fp.endswith(".tsx"):
            fixed_code, fixed_count = _fix_undefined_image_refs(code, defined_assets, fp)
            if fixed_count > 0:
                files[fp] = fixed_code
                total_fixed += fixed_count
    if total_fixed > 0:
        print(f"[FigmaAssemblyNode] Fixed {total_fixed} undefined image references")

    # 8. Sanitize Figma artifacts
    for fp, code in list(files.items()):
        if fp.startswith("/components/") and fp.endswith(".tsx"):
            cleaned = _sanitize_figma_artifacts(code)
            if cleaned != code:
                files[fp] = cleaned

    # 9. Local UI component fallbacks
    fallback_stats = add_missing_ui_fallbacks(files)
    if fallback_stats["uiFallbacksAdded"] > 0:
        categories["uiFallbacks"] = fallback_stats["uiFallbacksAdded"]
        print(f"[FigmaAssemblyNode] Added {fallback_stats['uiFallbacksAdded']} local UI fallback files")
    if fallback_stats["unknownUiImports"] > 0:
        print(f"[FigmaAssemblyNode] Unknown @/components/ui imports: {fallback_stats['unknownUiImports']}")

    package_fallback_stats = add_local_package_fallbacks(files)
    if package_fallback_stats["packageFallbacksAdded"] > 0:
        categories["packageFallbacks"] = package_fallback_stats["packageFallbacksAdded"]
        print(
            f"[FigmaAssemblyNode] Added {package_fallback_stats['packageFallbacksAdded']} local package fallback files"
        )

    # 10. Dependency scanning + package.json
    if template_pkg:
        code_files = [
            {"path": p, "code": c}
            for p, c in files.items()
            if p.endswith((".ts", ".tsx", ".js", ".jsx"))
        ]
        scanned_deps = scan_dependencies(code_files)
        build_result = build_package_json(scanned_deps, template_pkg)
        add_file("/package.json", json.dumps(build_result["packageJson"], indent=2), "config")

    total_files = len(files)
    print(f"\n[FigmaAssemblyNode] Assembly complete: {total_files} files")
    print(f"Categories: {json.dumps(categories)}")

    return {
        "files": {
            "files": files,
            "stats": {"totalFiles": total_files, "categories": categories},
        }
    }
