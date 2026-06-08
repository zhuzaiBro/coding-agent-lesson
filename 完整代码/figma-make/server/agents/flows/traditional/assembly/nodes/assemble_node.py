"""step16: File assembly node (no LLM, pure Python)."""
import json
from pathlib import Path

from agents.utils.dependency_builder import build_package_json, scan_dependencies
from agents.utils.local_package_fallbacks import add_local_package_fallbacks
from agents.utils.ui_component_fallbacks import add_missing_ui_fallbacks


def _normalize_path(file_path: str) -> str:
    """Normalize file path for Sandpack (no /src/ prefix)."""
    normalized = file_path if file_path.startswith("/") else f"/{file_path}"
    if normalized.startswith("/src/"):
        normalized = normalized[4:]  # Remove /src
    return normalized


async def assemble_node(state: dict) -> dict:
    """Assemble all generated code artifacts into Sandpack-compatible files dict."""
    print("--- AssembleNode Start ---")

    files: dict = {}
    categories: dict = {}

    def add_file(file_path: str, content: str, category: str):
        normalized = _normalize_path(file_path)
        files[normalized] = content
        categories[category] = categories.get(category, 0) + 1

    def add_files(items, category: str, code_key: str = "content"):
        if not items:
            return
        for item in items:
            path = item.get("path") if isinstance(item, dict) else getattr(item, "path", None)
            content = item.get(code_key) if isinstance(item, dict) else getattr(item, code_key, None)
            if path and content:
                add_file(path, content, category)

    # ========================================
    # 1. Template files
    # ========================================
    try:
        index_path = Path.cwd() / "templates" / "react-ts" / "index.tsx"
        index_content = index_path.read_text(encoding="utf-8")
        add_file("/index.tsx", index_content, "entry")
    except Exception as e:
        print(f"[AssembleNode] Warning: Failed to read index.tsx template: {e}")
        add_file(
            "/index.tsx",
            """import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

const root = createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""",
            "entry",
        )

    # ========================================
    # 2. Single-file artifacts
    # ========================================

    # step8: utils (files array with code field)
    utils = state.get("utils", {})
    if utils and utils.get("files"):
        for f in utils["files"]:
            path = f.get("path") if isinstance(f, dict) else getattr(f, "path", None)
            code = f.get("code") if isinstance(f, dict) else getattr(f, "code", None)
            if path and code:
                add_file(path, code, "utils")

    # step14: global styles
    styles = state.get("styles", {})
    if styles:
        s_path = styles.get("path") if isinstance(styles, dict) else getattr(styles, "path", None)
        s_content = styles.get("content") if isinstance(styles, dict) else getattr(styles, "content", None)
        if s_path and s_content:
            add_file(s_path, s_content, "styles")

    # step15: App.tsx
    app = state.get("app", {})
    if app:
        a_path = app.get("path") if isinstance(app, dict) else getattr(app, "path", None)
        a_content = app.get("content") if isinstance(app, dict) else getattr(app, "content", None)
        if a_path and a_content:
            add_file(a_path, a_content, "entry")

    # ========================================
    # 3. Array artifacts
    # ========================================

    # step7: types (files array with code field)
    types = state.get("types", {})
    if types and types.get("files"):
        for f in types["files"]:
            path = f.get("path") if isinstance(f, dict) else getattr(f, "path", None)
            code = f.get("code") if isinstance(f, dict) else getattr(f, "code", None)
            if path and code:
                add_file(path, code, "types")

    # step9: mock data (files array with content field)
    mock_data = state.get("mockData", {})
    if mock_data:
        add_files(mock_data.get("files", []) if isinstance(mock_data, dict) else [], "mockData")

    # step10: service (files array with content field)
    service = state.get("service", {})
    if service:
        add_files(service.get("files", []) if isinstance(service, dict) else [], "service")

    # step11: hooks (files array with content field)
    hooks = state.get("hooks", {})
    if hooks:
        add_files(hooks.get("files", []) if isinstance(hooks, dict) else [], "hooks")

    # step12: components (content field)
    components_code = state.get("componentsCode", [])
    if components_code:
        print(f"[AssembleNode] componentsCode count: {len(components_code)}")
        add_files(components_code, "components")

    # step13: pages (content field)
    pages_code = state.get("pagesCode", [])
    if pages_code:
        print(f"[AssembleNode] pagesCode count: {len(pages_code)}")
        add_files(pages_code, "pages")

    # step14.5: layouts (content field)
    layouts = state.get("layouts", {})
    if layouts:
        layouts_code = layouts.get("layoutsCode", []) if isinstance(layouts, dict) else []
        if layouts_code:
            print(f"[AssembleNode] layoutsCode count: {len(layouts_code)}")
            add_files(layouts_code, "layouts")

    # ========================================
    # 3.25 Local UI component fallbacks
    # ========================================
    fallback_stats = add_missing_ui_fallbacks(files)
    if fallback_stats["uiFallbacksAdded"] > 0:
        categories["uiFallbacks"] = fallback_stats["uiFallbacksAdded"]
        print(f"[AssembleNode] Added {fallback_stats['uiFallbacksAdded']} local UI fallback files")
    if fallback_stats["unknownUiImports"] > 0:
        print(f"[AssembleNode] Unknown @/components/ui imports: {fallback_stats['unknownUiImports']}")

    package_fallback_stats = add_local_package_fallbacks(files)
    if package_fallback_stats["packageFallbacksAdded"] > 0:
        categories["packageFallbacks"] = package_fallback_stats["packageFallbacksAdded"]
        print(
            f"[AssembleNode] Added {package_fallback_stats['packageFallbacksAdded']} local package fallback files"
        )

    # ========================================
    # 3.5 Programmatic dependency analysis + package.json
    # ========================================
    dependency = state.get("dependency", {})
    if dependency:
        pkg_json = dependency.get("packageJson") if isinstance(dependency, dict) else None
        if pkg_json:
            code_files = [
                {"path": p, "code": c}
                for p, c in files.items()
                if p.endswith((".ts", ".tsx", ".js", ".jsx"))
            ]
            print(f"[AssembleNode] Scanning imports from {len(code_files)} code files...")

            scanned_deps = scan_dependencies(code_files)
            print(f"[AssembleNode] Found {len(scanned_deps)} third-party packages from imports")

            build_result = build_package_json(scanned_deps, pkg_json)
            final_pkg = build_result["packageJson"]
            added_deps = build_result.get("dependencies", {})

            if added_deps:
                print(f"[AssembleNode] Added {len(added_deps)} new dependencies: {', '.join(added_deps.keys())}")

            add_file("/package.json", json.dumps(final_pkg, indent=2), "config")

    # ========================================
    # 4. Stats & logging
    # ========================================
    total_files = len(files)
    print(f"--- AssembleNode Complete ---")
    print(f"Total files: {total_files}")
    print(f"Categories: {json.dumps(categories)}")

    return {
        "files": {
            "files": files,
            "stats": {
                "totalFiles": total_files,
                "categories": categories,
            },
        }
    }
