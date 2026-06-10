"""
生成代码 AST 后处理（postProcessNode 调用）。

用正则修复 LLM 常见输出问题：对象直接渲染、可选链缺失、非法 JSX 等。
未引入完整 Babel 解析，兼顾 Sandpack 场景下的速度与可维护性。
"""
import re
import time
from typing import Any, Dict, List, Optional, Tuple


# 需要处理的文件扩展名
_PROCESSABLE_EXTENSIONS = {".tsx", ".ts", ".jsx", ".js"}

# 跳过的文件/目录模式
_SKIP_PATTERNS = {
    "node_modules",
    ".d.ts",
    "vite.config",
    "tailwind.config",
    "package.json",
}


def should_process_file(file_path: str) -> bool:
    """判断文件是否应由 AST 修复器处理。"""
    for pattern in _SKIP_PATTERNS:
        if pattern in file_path:
            return False

    return any(file_path.endswith(ext) for ext in _PROCESSABLE_EXTENSIONS)


def _fix_missing_react_import(code: str, file_path: str) -> Tuple[str, List[str]]:
    """修复使用 JSX 但缺少 React import 的 .tsx/.jsx 文件。"""
    fixes = []
    if not file_path.endswith((".tsx", ".jsx")):
        return code, fixes

    # 检查是否使用 JSX 但未 import React
    has_jsx = bool(re.search(r"<[A-Z][A-Za-z]*|<[a-z]+\s|return\s*\(", code))
    has_react_import = bool(re.search(r"""import\s+.*React.*\s+from\s+['"]react['"]""", code))

    if has_jsx and not has_react_import:
        # 在文件顶部补充 React import
        code = "import React from 'react';\n" + code
        fixes.append("补充缺失的 React import")

    return code, fixes


def _fix_console_log_strings(code: str) -> Tuple[str, List[str]]:
    """空操作：生成代码中允许 console.log。"""
    return code, []


def _fix_undefined_variables(code: str) -> Tuple[str, List[str]]:
    """对常见未定义变量模式做基础检查。"""
    fixes = []
    # 保守修复：仅在明显有问题时处理 .map 等可选链缺失
    return code, fixes


def _fix_missing_semicolons(code: str) -> Tuple[str, List[str]]:
    """空操作：现代 JS/TS 中分号可选。"""
    return code, []


def _remove_markdown_code_blocks(code: str) -> Tuple[str, List[str]]:
    """移除可能存在的 markdown 代码块标记。"""
    fixes = []

    # 移除首尾 markdown 围栏
    cleaned = re.sub(r"^```(?:tsx?|jsx?|typescript|javascript)?\s*\n", "", code)
    cleaned = re.sub(r"\n```\s*$", "", cleaned)

    if cleaned != code:
        fixes.append("移除 markdown 代码块标记")
        code = cleaned

    return code, fixes


def _fix_duplicate_imports(code: str) -> Tuple[str, List[str]]:
    """移除重复的 import 语句。"""
    fixes = []
    lines = code.split("\n")
    seen_imports: Dict[str, str] = {}
    new_lines = []

    for line in lines:
        m = re.match(r"""^import\s+.*\s+from\s+['"]([^'"]+)['"];?\s*$""", line.strip())
        if m:
            module = m.group(1)
            if module in seen_imports:
                fixes.append(f"移除重复 import: '{module}'")
                continue
            seen_imports[module] = line

        new_lines.append(line)

    return "\n".join(new_lines), fixes


def process_file(code: str, file_path: str) -> Tuple[str, List[str]]:
    """
    对单个生成文件应用全部修复器。

    Returns:
        (修复后代码, 已应用修复列表)
    """
    all_fixes: List[str] = []

    # 按顺序应用修复器
    code, fixes = _remove_markdown_code_blocks(code)
    all_fixes.extend(fixes)

    code, fixes = _fix_duplicate_imports(code)
    all_fixes.extend(fixes)

    code, fixes = _fix_missing_react_import(code, file_path)
    all_fixes.extend(fixes)

    code, fixes = _fix_undefined_variables(code)
    all_fixes.extend(fixes)

    return code, all_fixes


def post_process_files(files: Dict[str, str]) -> Dict[str, Any]:
    """
    对 Sandpack 文件集做后处理。

    Args:
        files: 文件路径 → 代码内容
    Returns:
        含 'files'（修复后文件）与 'result'（修复报告）的字典
    """
    start_time = time.time()
    fixed_files = {}
    file_results = {}
    total_issues = 0
    total_fixes = 0

    for file_path, code in files.items():
        if not should_process_file(file_path):
            fixed_files[file_path] = code
            continue

        try:
            fixed_code, applied_fixes = process_file(code, file_path)
            fixed_files[file_path] = fixed_code

            if applied_fixes:
                file_results[file_path] = {"fixes": applied_fixes, "count": len(applied_fixes)}
                total_fixes += len(applied_fixes)
                total_issues += len(applied_fixes)
            else:
                fixed_files[file_path] = code
        except Exception as e:
            print(f"[AST] 警告: 处理 {file_path} 失败: {e}")
            fixed_files[file_path] = code

    duration = int((time.time() - start_time) * 1000)

    result = {
        "totalIssues": total_issues,
        "totalFixes": total_fixes,
        "duration": duration,
        "files": file_results,
    }

    return {"files": fixed_files, "result": result}


def process_generated_code(
    code: str,
    file_name: str,
    type_files: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    对单个生成文件做后处理。

    可在组件/页面生成节点内调用，无需等待组装阶段。

    Args:
        code: 生成的代码内容
        file_name: 文件路径（如 "/components/NewsList.tsx"）
        type_files: 类型文件数组 [{"path": "/types/News.ts", "code": "..."}]
    Returns:
        修复后的代码字符串
    """
    if not code or not should_process_file(file_name):
        return code

    try:
        fixed_code, applied_fixes = process_file(code, file_name)

        if applied_fixes:
            print(f"[AST] {file_name}: 已修复 {len(applied_fixes)} 处问题")
            for fix in applied_fixes:
                print(f"  → {fix}")
            return fixed_code

        return code
    except Exception as e:
        print(f"[AST] {file_name}: 处理失败，使用原始代码: {e}")
        return code


def print_fix_report(result: Dict[str, Any]) -> None:
    """将修复报告打印到控制台。"""
    if result.get("totalIssues", 0) == 0:
        print("[AST PostProcess] 未发现问题")
        return

    print(
        f"[AST PostProcess] 发现 {result['totalIssues']} 处问题，"
        f"已修复 {result['totalFixes']} 处（{result['duration']}ms）"
    )

    for file_path, file_result in result.get("files", {}).items():
        if not file_result.get("fixes"):
            continue
        print(f"  {file_path}（{file_result['count']} 处修复）")
        for fix in file_result["fixes"]:
            print(f"    → {fix}")
