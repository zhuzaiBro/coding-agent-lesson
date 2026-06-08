"""Compile-check generated frontend files with a temporary Vite project."""
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from agents.utils.local_package_fallbacks import add_local_package_fallbacks
from agents.utils.ui_component_fallbacks import add_missing_ui_fallbacks


SOURCE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".css", ".scss", ".sass")
ROOT_CONFIG_FILES = {
    "/package.json",
    "/index.html",
    "/vite.config.ts",
    "/vite.config.js",
    "/tsconfig.json",
    "/tsconfig.app.json",
    "/tsconfig.node.json",
    "/tailwind.config.ts",
    "/tailwind.config.js",
    "/postcss.config.js",
}


class FrontendCompileError(RuntimeError):
    """Raised when generated frontend files fail to install or build."""


def _normalize_sandpack_path(path: str) -> str:
    if not path:
        return "/unknown.txt"
    normalized = path if path.startswith("/") else f"/{path}"
    return normalized.replace("\\", "/")


def _source_output_path(path: str) -> str:
    """Map Sandpack-style paths to a Vite project filesystem path."""
    normalized = _normalize_sandpack_path(path)
    if normalized.startswith("/src/"):
        return normalized.lstrip("/")
    return f"src/{normalized.lstrip('/')}"


def _get_file_map(assembled_files: Any) -> Dict[str, str]:
    if not isinstance(assembled_files, dict):
        return {}
    raw_files = assembled_files.get("files", assembled_files)
    if not isinstance(raw_files, dict):
        return {}
    return {
        _normalize_sandpack_path(path): str(content)
        for path, content in raw_files.items()
        if isinstance(path, str) and content is not None
    }


def _load_package_json(file_map: Dict[str, str]) -> Dict[str, Any]:
    raw_package = file_map.get("/package.json")
    if raw_package:
        try:
            parsed = json.loads(raw_package)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {
        "name": "generated-react-app",
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {"build": "vite build"},
        "dependencies": {
            "react": "^18.3.1",
            "react-dom": "^18.3.1",
        },
        "devDependencies": {},
    }


def _normalize_package_json(package_json: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(package_json)
    normalized.setdefault("name", "generated-react-app")
    normalized.setdefault("private", True)
    normalized.setdefault("version", "0.0.0")
    normalized.setdefault("type", "module")

    scripts = dict(normalized.get("scripts") or {})
    scripts.setdefault("build", "vite build")
    normalized["scripts"] = scripts

    deps = dict(normalized.get("dependencies") or {})
    deps.setdefault("react", "^18.3.1")
    deps.setdefault("react-dom", "^18.3.1")
    normalized["dependencies"] = deps

    dev_deps = dict(normalized.get("devDependencies") or {})
    dev_deps.setdefault("@vitejs/plugin-react-swc", "^3.10.2")
    dev_deps.setdefault("vite", "^6.3.5")
    dev_deps.setdefault("typescript", "^5.8.3")
    dev_deps.setdefault("@types/react", "^18.3.18")
    dev_deps.setdefault("@types/react-dom", "^18.3.5")
    dev_deps.setdefault("tailwindcss", "^3.4.17")
    dev_deps.setdefault("postcss", "^8.5.3")
    dev_deps.setdefault("autoprefixer", "^10.4.21")
    normalized["devDependencies"] = dev_deps

    return normalized


def _entry_file_name(file_map: Dict[str, str]) -> str:
    for candidate in ("/src/index.tsx", "/index.tsx", "/src/main.tsx", "/main.tsx"):
        if candidate in file_map:
            return Path(_source_output_path(candidate)).name
    return "index.tsx"


def _default_index_tsx() -> str:
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


def _default_app_tsx() -> str:
    return """export default function App() {
  return <main />;
}
"""


def _default_index_html(entry_name: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Generated App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/{entry_name}"></script>
  </body>
</html>
"""


def _vite_config() -> str:
    return """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
"""


def _tsconfig() -> str:
    return """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": false,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": []
}
"""


def _tailwind_config() -> str:
    return """/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
};
"""


def _postcss_config() -> str:
    return """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""


def _write_file(root: Path, relative_path: str, content: str) -> None:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _prepare_project(project_dir: Path, file_map: Dict[str, str]) -> Dict[str, str]:
    normalized_package = _normalize_package_json(_load_package_json(file_map))
    prepared = dict(file_map)
    prepared["/package.json"] = json.dumps(normalized_package, indent=2)
    add_missing_ui_fallbacks(prepared)
    add_local_package_fallbacks(prepared)

    entry_name = _entry_file_name(prepared)
    prepared.setdefault("/index.html", _default_index_html(entry_name))
    prepared.setdefault("/vite.config.ts", _vite_config())
    prepared.setdefault("/tsconfig.json", _tsconfig())
    prepared.setdefault("/tailwind.config.js", _tailwind_config())
    prepared.setdefault("/postcss.config.js", _postcss_config())

    has_entry = any(path in prepared for path in ("/src/index.tsx", "/index.tsx", "/src/main.tsx", "/main.tsx"))
    if not has_entry:
        prepared["/index.tsx"] = _default_index_tsx()
    if not any(path in prepared for path in ("/src/App.tsx", "/App.tsx", "/src/App.jsx", "/App.jsx")):
        prepared["/App.tsx"] = _default_app_tsx()
    if not any(path in prepared for path in ("/src/styles.css", "/styles.css")):
        prepared["/styles.css"] = ""

    for path, content in prepared.items():
        if path in ROOT_CONFIG_FILES:
            _write_file(project_dir, path.lstrip("/"), content)
        elif path.endswith(SOURCE_SUFFIXES):
            _write_file(project_dir, _source_output_path(path), content)

    return prepared


def _run_command(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "CI": "1", "npm_config_audit": "false", "npm_config_fund": "false"},
        )
    except subprocess.TimeoutExpired as exc:
        command_text = " ".join(command)
        raise FrontendCompileError(f"Frontend command timed out after {timeout}s: {command_text}") from exc


def _format_process_error(step: str, result: subprocess.CompletedProcess[str]) -> str:
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if len(output) > 6000:
        output = output[-6000:]
    return f"Frontend {step} failed with exit code {result.returncode}:\n{output}"


def compile_frontend_files_sync(
    assembled_files: Any,
    *,
    install_timeout: Optional[int] = None,
    build_timeout: Optional[int] = None,
    keep_temp: bool = False,
) -> Dict[str, Any]:
    """Install dependencies and run `npm run build` for generated files."""
    file_map = _get_file_map(assembled_files)
    if not file_map:
        raise FrontendCompileError("No generated frontend files were found to compile.")

    npm_path = shutil.which("npm")
    if not npm_path:
        raise FrontendCompileError("npm was not found, cannot compile-check generated frontend files.")

    install_timeout = install_timeout or int(os.getenv("FRONTEND_COMPILE_INSTALL_TIMEOUT", "180"))
    build_timeout = build_timeout or int(os.getenv("FRONTEND_COMPILE_BUILD_TIMEOUT", "90"))

    temp_dir = tempfile.mkdtemp(prefix="frontend-compile-")
    project_dir = Path(temp_dir)
    try:
        prepared_files = _prepare_project(project_dir, file_map)

        install = _run_command([npm_path, "install", "--package-lock=false"], project_dir, install_timeout)
        if install.returncode != 0:
            raise FrontendCompileError(_format_process_error("dependency install", install))

        build = _run_command([npm_path, "run", "build"], project_dir, build_timeout)
        if build.returncode != 0:
            raise FrontendCompileError(_format_process_error("build", build))

        return {
            "ok": True,
            "files": prepared_files,
            "stats": {
                "compileChecked": True,
                "compileCommand": "npm run build",
                "compiledFiles": len(prepared_files),
            },
        }
    finally:
        if keep_temp:
            print(f"[FrontendCompile] Kept temp project: {project_dir}")
        else:
            shutil.rmtree(project_dir, ignore_errors=True)


async def compile_frontend_files(assembled_files: Any) -> Dict[str, Any]:
    """Async wrapper for graph nodes."""
    return await asyncio.to_thread(compile_frontend_files_sync, assembled_files)
