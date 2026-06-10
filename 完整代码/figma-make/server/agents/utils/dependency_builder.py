"""
程序化依赖分析器（无 LLM，确定性）

扫描 LLM 生成的代码文件中的 import 语句，自动推断所需的第三方包，
然后与模板 package.json 合并，输出最终可运行的 package.json。

这个设计的原因：之前让 LLM 推断依赖（dependencyNode）经常出现幻觉，
比如推断了不存在的包版本；改为程序化扫描后准确率接近 100%。

流程：
  1. 遍历所有已生成的代码文件
  2. 从 import/require 中提取第三方包名（过滤相对路径和内置模块）
  3. 在 VERSION_MAP 中查找版本（未收录的 fallback 到 "latest"）
  4. 与模板 package.json 合并（模板中已有的版本优先）
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# ===================== 版本映射表 =====================

VERSION_MAP: Dict[str, str] = {
    # ===== React 生态 =====
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "react-hook-form": "^7.55.0",

    # ===== 状态管理 =====
    "zustand": "^4.5.0",
    "jotai": "^2.6.0",
    "@reduxjs/toolkit": "^2.0.0",
    "react-redux": "^9.1.0",
    "recoil": "^0.7.0",

    # ===== UI 组件库 =====
    "lucide-react": "^0.487.0",
    "react-icons": "^5.3.0",
    "@heroicons/react": "^2.1.0",
    "@radix-ui/react-accordion": "^1.2.0",
    "@radix-ui/react-alert-dialog": "^1.1.0",
    "@radix-ui/react-avatar": "^1.1.0",
    "@radix-ui/react-checkbox": "^1.1.0",
    "@radix-ui/react-collapsible": "^1.1.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-dropdown-menu": "^2.1.0",
    "@radix-ui/react-hover-card": "^1.1.0",
    "@radix-ui/react-label": "^2.1.0",
    "@radix-ui/react-menubar": "^1.1.0",
    "@radix-ui/react-navigation-menu": "^1.2.0",
    "@radix-ui/react-popover": "^1.1.0",
    "@radix-ui/react-progress": "^1.1.0",
    "@radix-ui/react-radio-group": "^1.2.0",
    "@radix-ui/react-scroll-area": "^1.2.0",
    "@radix-ui/react-select": "^2.1.0",
    "@radix-ui/react-separator": "^1.1.0",
    "@radix-ui/react-slider": "^1.2.0",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-switch": "^1.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-toast": "^1.2.0",
    "@radix-ui/react-toggle": "^1.1.0",
    "@radix-ui/react-toggle-group": "^1.1.0",
    "@radix-ui/react-tooltip": "^1.1.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4",
    "tailwindcss-animate": "^1.0.7",
    "cmdk": "^1.0.0",

    # ===== 图表 =====
    "recharts": "^2.15.2",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0",
    "d3": "^7.9.0",
    "nivo": "^0.87.0",

    # ===== 日期时间 =====
    "date-fns": "^3.6.0",
    "dayjs": "^1.11.0",
    "react-day-picker": "^8.10.1",
    "moment": "^2.30.0",

    # ===== 动画 =====
    "framer-motion": "^11.0.0",
    "react-spring": "^9.7.0",
    "react-transition-group": "^4.4.0",
    "auto-animate": "^0.8.0",
    "@formkit/auto-animate": "^0.8.0",

    # ===== 表单/校验 =====
    "zod": "^3.23.0",
    "yup": "^1.4.0",
    "@hookform/resolvers": "^3.9.0",

    # ===== HTTP 请求 =====
    "axios": "^1.7.0",
    "swr": "^2.2.0",
    "@tanstack/react-query": "^5.50.0",
    "ky": "^1.4.0",

    # ===== 富文本/Markdown =====
    "react-markdown": "^9.0.0",
    "react-quill": "^2.0.0",
    "remark-gfm": "^4.0.0",
    "@tiptap/react": "^2.6.0",
    "react-syntax-highlighter": "^15.5.0",
    "highlight.js": "^11.10.0",
    "prismjs": "^1.29.0",

    # ===== 表格/虚拟列表 =====
    "@tanstack/react-table": "^8.20.0",
    "react-virtualized": "^9.22.0",
    "react-virtuoso": "^4.7.0",
    "@tanstack/react-virtual": "^3.8.0",

    # ===== 拖拽 =====
    "@dnd-kit/core": "^6.1.0",
    "@dnd-kit/sortable": "^8.0.0",
    "react-beautiful-dnd": "^13.1.0",
    "react-dnd": "^16.0.0",

    # ===== 轮播/滑块 =====
    "embla-carousel-react": "^8.6.0",
    "swiper": "^11.1.0",

    # ===== Toast/通知 =====
    "sonner": "^2.0.3",
    "react-hot-toast": "^2.4.0",
    "react-toastify": "^10.0.0",
    "sweetalert2": "^11.12.0",

    # ===== 其他常用 =====
    "input-otp": "^1.4.2",
    "next-themes": "^0.4.6",
    "react-resizable-panels": "^2.1.7",
    "uuid": "^9.0.0",
    "nanoid": "^5.0.0",
    "lodash": "^4.17.0",
    "lodash-es": "^4.17.0",
    "immer": "^10.1.0",
    "react-helmet-async": "^2.0.0",
    "react-intersection-observer": "^9.10.0",
    "react-use": "^17.5.0",
    "usehooks-ts": "^3.1.0",
    "@headlessui/react": "^2.1.0",
    "react-dropzone": "^14.2.0",
    "react-i18next": "^14.1.0",
    "i18next": "^23.11.0",
    "react-error-boundary": "^4.0.0",
}

# 需排除的 Node.js 内置模块
_BUILTINS = frozenset([
    "fs", "path", "os", "url", "util", "http", "https", "stream",
    "crypto", "events", "buffer", "process", "child_process", "cluster",
    "net", "dns", "tls",
])


def _extract_package_name(module_path: str) -> Optional[str]:
    """从 import 路径提取包名。"""
    # 排除相对路径
    if module_path.startswith(("./", "../", "@/", "~/")):
        return None

    # 作用域包：@scope/package
    if module_path.startswith("@"):
        parts = module_path.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return None

    # 普通包：package/sub -> package
    pkg_name = module_path.split("/")[0]
    if pkg_name in _BUILTINS:
        return None

    return pkg_name


def extract_imports(code: str) -> Set[str]:
    """
    从代码中提取所有第三方包名。

    支持：
    - import xxx from 'package'
    - import { xxx } from 'package'
    - import 'package'
    - const xxx = require('package')
    - import('package')
    """
    packages: Set[str] = set()

    # 匹配 ES import 语句
    import_regex = r"""(?:import\s+(?:[\s\S]*?\s+from\s+)?['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\))"""
    for m in re.finditer(import_regex, code):
        module_path = m.group(1) or m.group(2)
        if module_path:
            pkg = _extract_package_name(module_path)
            if pkg:
                packages.add(pkg)

    # 匹配 require 语句
    require_regex = r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""
    for m in re.finditer(require_regex, code):
        module_path = m.group(1)
        if module_path:
            pkg = _extract_package_name(module_path)
            if pkg:
                packages.add(pkg)

    return packages


def scan_dependencies(files: List[Dict[str, Any]]) -> Dict[str, str]:
    """扫描所有文件并提取第三方依赖。"""
    all_packages: Set[str] = set()

    for file in files:
        code = file.get("code") or file.get("content") or ""
        if not code:
            continue
        packages = extract_imports(code)
        all_packages.update(packages)

    deps: Dict[str, str] = {}
    for pkg in all_packages:
        version = VERSION_MAP.get(pkg, "latest")
        deps[pkg] = version
        if pkg not in VERSION_MAP:
            print(f'[DependencyBuilder] 未知包 "{pkg}" → 使用 "latest"')

    return deps


def build_package_json(
    scanned_deps: Dict[str, str],
    template_package_json: Any,
) -> Dict[str, Any]:
    """
    合并扫描依赖与模板，构建完整 package.json。

    合并策略：模板版本优先（避免核心库被降级）。
    """
    template_deps = template_package_json.get("dependencies", {})

    merged_dependencies = dict(template_deps)
    added_deps: Dict[str, str] = {}

    for pkg, version in scanned_deps.items():
        if pkg not in merged_dependencies:
            merged_dependencies[pkg] = version
            added_deps[pkg] = version
            print(f"[DependencyBuilder] 添加依赖: {pkg}@{version}")

    return {
        "packageJson": {
            **template_package_json,
            "dependencies": merged_dependencies,
        },
        "dependencies": added_deps,
        "reason": "从代码 import 语句自动分析，程序化推断依赖",
    }


async def read_template_package_json() -> Any:
    """读取模板 package.json。"""
    template_path = Path.cwd() / "templates" / "react-ts" / "package.json"

    try:
        content = template_path.read_text(encoding="utf-8")
        return json.loads(content)
    except Exception as e:
        print(f"[DependencyBuilder] 读取模板失败: {template_path}: {e}")
        # 兜底：返回最小模板
        return {
            "name": "react-project",
            "private": True,
            "version": "0.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
            },
            "dependencies": {
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
            },
            "devDependencies": {
                "@vitejs/plugin-react-swc": "^3.10.2",
                "tailwindcss": "^3.4.17",
                "vite": "6.3.5",
            },
        }
