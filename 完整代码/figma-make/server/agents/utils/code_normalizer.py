"""
代码标准化工具

修复 LLM 生成代码中的常见格式问题，特别是换行符转义问题。
LLM 有时会将换行符写成字面字符串 "\\n" 而非真正的换行，导致 Sandpack 解析异常。

典型场景：structured output 模式下 LLM 输出 JSON，JSON 字符串内的代码
会把换行符转义为 "\\n"，取出后需要还原。
"""
from typing import Any, Dict, List, Optional, TypeVar

T = TypeVar("T", bound=dict)


def normalize_code_content(content: str) -> str:
    """
    Fix escaped newline issues in code.

    Replaces literal "\\n" with real newlines, "\\t" with tabs, etc.
    """
    if not content:
        return content

    has_literal_escapes = (
        "\\n" in content or
        "\\t" in content or
        '\\"' in content
    )

    if not has_literal_escapes:
        return content

    normalized = content
    normalized = normalized.replace("\\n", "\n")
    normalized = normalized.replace("\\t", "\t")
    normalized = normalized.replace('\\"', '"')
    normalized = normalized.replace("\\'", "'")

    return normalized


def normalize_code_file(file: dict) -> dict:
    """
    Normalize a single code file object.
    Supports { content: str } or { code: str } format.
    """
    if not file:
        return file

    result = dict(file)

    if result.get("content"):
        result["content"] = normalize_code_content(result["content"])

    if result.get("code"):
        result["code"] = normalize_code_content(result["code"])

    return result


def normalize_code_files(files: List[dict]) -> List[dict]:
    """Batch normalize a list of code file objects."""
    if not files or not isinstance(files, list):
        return files
    return [normalize_code_file(f) for f in files]


def normalize_llm_result(result: Any) -> Any:
    """
    Normalize LLM generation result.
    Automatically detects and handles various common output formats.
    """
    if not result or not isinstance(result, dict):
        return result

    normalized = dict(result)

    # Handle single content field
    if isinstance(normalized.get("content"), str):
        normalized["content"] = normalize_code_content(normalized["content"])

    # Handle single code field
    if isinstance(normalized.get("code"), str):
        normalized["code"] = normalize_code_content(normalized["code"])

    # Handle files array (common in utils, types, hooks, etc.)
    if isinstance(normalized.get("files"), list):
        normalized["files"] = normalize_code_files(normalized["files"])

    # Handle layoutsCode array (layout node)
    if isinstance(normalized.get("layoutsCode"), list):
        normalized["layoutsCode"] = normalize_code_files(normalized["layoutsCode"])

    # Handle componentsCode array
    if isinstance(normalized.get("componentsCode"), list):
        normalized["componentsCode"] = normalize_code_files(normalized["componentsCode"])

    return normalized
