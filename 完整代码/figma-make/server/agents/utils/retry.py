"""
LLM 调用通用重试执行器

关键设计：重试时将上一次的报错信息以 HumanMessage 形式追加到对话历史，
让 LLM 能"看到"自己的错误并自我修正，而不是盲目重试相同的输入。
这对 structured output（函数调用）特别有效，因为 JSON 格式错误是可自愈的。
"""
from typing import Any, Callable, List, Optional

from langchain_core.messages import HumanMessage

DEFAULT_MAX_RETRIES = 3


def _default_error_feedback(error: Exception) -> str:
    return (
        f"⚠️ The previous generation failed with error:\n{str(error)}\n\n"
        "Please carefully check and fix the following issues:\n"
        "1. Ensure all enum fields use only schema-defined valid values\n"
        "2. Ensure JSON format is correct with no missing required fields\n"
        "3. Ensure code syntax is correct\n\n"
        "Please regenerate the correct output:"
    )


async def with_retry(
    model: Any,
    messages: List[Any],
    max_retries: int = DEFAULT_MAX_RETRIES,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    format_error_feedback: Optional[Callable[[Exception], str]] = None,
) -> Any:
    """
    LLM call executor with retry capability.

    On retry, automatically appends error feedback message to let LLM correct its output.

    Args:
        model: Invokable model (must have ainvoke method)
        messages: Initial messages list
        max_retries: Maximum number of retry attempts
        on_retry: Callback called on each retry (attempt, error)
        format_error_feedback: Custom error feedback message generator
    Returns:
        Execution result
    """
    feedback_fn = format_error_feedback or _default_error_feedback
    last_error: Optional[Exception] = None
    current_messages = list(messages)

    for attempt in range(1, max_retries + 1):
        try:
            return await model.ainvoke(current_messages)
        except Exception as error:
            last_error = error if isinstance(error, Exception) else Exception(str(error))

            if attempt < max_retries:
                if on_retry:
                    on_retry(attempt, last_error)
                # Append error feedback for next retry
                current_messages = list(messages) + [HumanMessage(content=feedback_fn(last_error))]

    raise last_error
