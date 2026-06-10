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
        f"⚠️ 上一次生成失败，错误信息：\n{str(error)}\n\n"
        "请仔细检查并修复以下问题：\n"
        "1. 确保所有枚举字段仅使用 schema 定义的有效值\n"
        "2. 确保 JSON 格式正确，无缺失必填字段\n"
        "3. 确保代码语法正确\n\n"
        "请重新生成正确的输出："
    )


async def with_retry(
    model: Any,
    messages: List[Any],
    max_retries: int = DEFAULT_MAX_RETRIES,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    format_error_feedback: Optional[Callable[[Exception], str]] = None,
) -> Any:
    """
    带重试能力的 LLM 调用执行器。

    重试时自动追加错误反馈消息，让 LLM 修正输出。

    Args:
        model: 可调用模型（需有 ainvoke 方法）
        messages: 初始消息列表
        max_retries: 最大重试次数
        on_retry: 每次重试时的回调 (attempt, error)
        format_error_feedback: 自定义错误反馈消息生成器
    Returns:
        执行结果
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
                # 追加错误反馈供下次重试使用
                current_messages = list(messages) + [HumanMessage(content=feedback_fn(last_error))]

    raise last_error
