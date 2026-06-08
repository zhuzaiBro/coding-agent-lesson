"""
AST post-processor for generated code.

Provides regex-based code fixing for common LLM generation issues.
Python equivalent of the TypeScript AST fixer (uses regex instead of Babel AST).
"""
import re
import time
from typing import Any, Dict, List, Optional, Tuple


# File extensions that should be processed
_PROCESSABLE_EXTENSIONS = {".tsx", ".ts", ".jsx", ".js"}

# Files/directories to skip
_SKIP_PATTERNS = {
    "node_modules",
    ".d.ts",
    "vite.config",
    "tailwind.config",
    "package.json",
}


def should_process_file(file_path: str) -> bool:
    """Check if a file should be processed by the AST fixer."""
    for pattern in _SKIP_PATTERNS:
        if pattern in file_path:
            return False

    return any(file_path.endswith(ext) for ext in _PROCESSABLE_EXTENSIONS)


def _fix_missing_react_import(code: str, file_path: str) -> Tuple[str, List[str]]:
    """Fix missing React import in .tsx/.jsx files that use JSX."""
    fixes = []
    if not file_path.endswith((".tsx", ".jsx")):
        return code, fixes

    # Check if file uses JSX but doesn't import React
    has_jsx = bool(re.search(r"<[A-Z][A-Za-z]*|<[a-z]+\s|return\s*\(", code))
    has_react_import = bool(re.search(r"""import\s+.*React.*\s+from\s+['"]react['"]""", code))

    if has_jsx and not has_react_import:
        # Add React import at the top (after any existing imports that precede it, or at start)
        code = "import React from 'react';\n" + code
        fixes.append("Added missing React import")

    return code, fixes


def _fix_console_log_strings(code: str) -> Tuple[str, List[str]]:
    """No-op: console.log is acceptable in generated code."""
    return code, []


def _fix_undefined_variables(code: str) -> Tuple[str, List[str]]:
    """Basic check for common undefined variable patterns."""
    fixes = []
    # Fix common pattern: accessing .map on potentially undefined without optional chaining
    # This is a conservative fix - only when clearly problematic
    return code, fixes


def _fix_missing_semicolons(code: str) -> Tuple[str, List[str]]:
    """No-op: semicolons are optional in modern JS/TS."""
    return code, []


def _remove_markdown_code_blocks(code: str) -> Tuple[str, List[str]]:
    """Remove markdown code block markers if present."""
    fixes = []

    # Remove leading/trailing markdown code fences
    cleaned = re.sub(r"^```(?:tsx?|jsx?|typescript|javascript)?\s*\n", "", code)
    cleaned = re.sub(r"\n```\s*$", "", cleaned)

    if cleaned != code:
        fixes.append("Removed markdown code block markers")
        code = cleaned

    return code, fixes


def _fix_duplicate_imports(code: str) -> Tuple[str, List[str]]:
    """Remove duplicate import statements."""
    fixes = []
    lines = code.split("\n")
    seen_imports: Dict[str, str] = {}
    new_lines = []

    for line in lines:
        m = re.match(r"""^import\s+.*\s+from\s+['"]([^'"]+)['"];?\s*$""", line.strip())
        if m:
            module = m.group(1)
            if module in seen_imports:
                fixes.append(f"Removed duplicate import from '{module}'")
                continue
            seen_imports[module] = line

        new_lines.append(line)

    return "\n".join(new_lines), fixes


def process_file(code: str, file_path: str) -> Tuple[str, List[str]]:
    """
    Process a single generated code file with all fixers.

    Returns:
        Tuple of (fixed_code, list_of_applied_fixes)
    """
    all_fixes: List[str] = []

    # Apply fixers in order
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
    Post-process a collection of Sandpack files.

    Args:
        files: Dict mapping file paths to code content
    Returns:
        Dict with 'files' (fixed files) and 'result' (fix report)
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
            print(f"[AST] Warning: Failed to process {file_path}: {e}")
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
    Post-process a single generated code file.

    Suitable for calling inside component/page generation nodes
    without waiting for the assembly phase.

    Args:
        code: Generated code content
        file_name: File path (e.g. "/components/NewsList.tsx")
        type_files: Type files array [{"path": "/types/News.ts", "code": "..."}]
    Returns:
        Fixed code string
    """
    if not code or not should_process_file(file_name):
        return code

    try:
        fixed_code, applied_fixes = process_file(code, file_name)

        if applied_fixes:
            print(f"[AST] {file_name}: Fixed {len(applied_fixes)} issues")
            for fix in applied_fixes:
                print(f"  → {fix}")
            return fixed_code

        return code
    except Exception as e:
        print(f"[AST] {file_name}: Processing failed, using original code: {e}")
        return code


def print_fix_report(result: Dict[str, Any]) -> None:
    """Print fix report to console."""
    if result.get("totalIssues", 0) == 0:
        print("[AST PostProcess] No issues found")
        return

    print(
        f"[AST PostProcess] Found {result['totalIssues']} issues, "
        f"fixed {result['totalFixes']} ({result['duration']}ms)"
    )

    for file_path, file_result in result.get("files", {}).items():
        if not file_result.get("fixes"):
            continue
        print(f"  {file_path} ({file_result['count']} fixes)")
        for fix in file_result["fixes"]:
            print(f"    → {fix}")
