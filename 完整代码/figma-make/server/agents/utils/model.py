"""
Multi-model architecture:
- DeepSeek: Main model option 1 (function calling support)
- GLM: Main model option 2 (ZhipuAI, function calling support)
- Qwen: Main model option 3 (DashScope OpenAI-compatible API)
- Qwen-VL: Vision model (image analysis only)

Switch main model via MAIN_MODEL_PROVIDER env var: deepseek | glm | qwen
"""
import os
from typing import Optional, Type

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from agents.utils.structured_model import StructuredModelWrapper

# Singleton instances
_deepseek_instance: Optional[ChatOpenAI] = None
_glm_instance: Optional[ChatOpenAI] = None
_qwen_text_instance: Optional[ChatOpenAI] = None
_qwen_vision_instance: Optional[ChatOpenAI] = None


def get_deepseek_model() -> ChatOpenAI:
    """Get DeepSeek main model instance."""
    global _deepseek_instance
    if _deepseek_instance is None:
        _deepseek_instance = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            temperature=0,
            max_tokens=8192,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
    return _deepseek_instance


def get_glm_model() -> ChatOpenAI:
    """Get GLM main model instance (ZhipuAI)."""
    global _glm_instance
    if _glm_instance is None:
        _glm_instance = ChatOpenAI(
            model=os.getenv("GLM_MODEL", "glm-4-flash"),
            api_key=os.getenv("GLM_API_KEY", ""),
            temperature=0,
            max_tokens=8192,
            base_url=os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
        )
    return _glm_instance


def _resolve_qwen_text_model() -> str:
    """Resolve Qwen text model for structured output / function calling."""
    explicit = os.getenv("QWEN_TEXT_MODEL")
    if explicit:
        return explicit

    legacy = os.getenv("QWEN_MODEL")
    if legacy and "vl" not in legacy.lower():
        return legacy

    return "qwen-plus"


def _resolve_qwen_vision_model() -> str:
    """Resolve Qwen vision model for image analysis."""
    return os.getenv("QWEN_VL_MODEL") or os.getenv("QWEN_MODEL") or "qwen-vl-max"


def _qwen_extra_body() -> dict:
    """DashScope: disable thinking so function_calling / tool_choice works."""
    enable = os.getenv("QWEN_ENABLE_THINKING", "false").lower() in ("1", "true", "yes")
    return {"enable_thinking": enable}


def get_qwen_model() -> ChatOpenAI:
    """Get Qwen text main model (DashScope compatible-mode API)."""
    global _qwen_text_instance
    if _qwen_text_instance is None:
        model = _resolve_qwen_text_model()
        if "vl" in model.lower():
            print(
                f"[Model] Warning: Qwen text model '{model}' looks like a vision model. "
                "Set QWEN_TEXT_MODEL=qwen-plus or qwen-max for code generation."
            )
        thinking = _qwen_extra_body().get("enable_thinking")
        if thinking:
            print(
                "[Model] Warning: QWEN_ENABLE_THINKING=true — structured output may fail; "
                "will fall back to JSON prompt mode."
            )
        _qwen_text_instance = ChatOpenAI(
            model=model,
            api_key=os.getenv("QWEN_API_KEY", ""),
            temperature=0,
            max_tokens=8192,
            base_url=os.getenv(
                "QWEN_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            model_kwargs={"extra_body": _qwen_extra_body()},
        )
    return _qwen_text_instance


def get_qwen_vision_model() -> ChatOpenAI:
    """Get Qwen-VL vision model instance (image analysis only)."""
    global _qwen_vision_instance
    if _qwen_vision_instance is None:
        _qwen_vision_instance = ChatOpenAI(
            model=_resolve_qwen_vision_model(),
            api_key=os.getenv("QWEN_API_KEY", ""),
            temperature=0.1,
            max_tokens=32768,
            base_url=os.getenv(
                "QWEN_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )
    return _qwen_vision_instance


def get_main_model() -> ChatOpenAI:
    """Get currently configured main model based on MAIN_MODEL_PROVIDER env var."""
    provider = os.getenv("MAIN_MODEL_PROVIDER", "deepseek").lower()

    if provider == "glm":
        print("[Model] Using GLM as main model")
        return get_glm_model()
    if provider == "qwen":
        print(f"[Model] Using Qwen as main model ({_resolve_qwen_text_model()})")
        return get_qwen_model()
    print("[Model] Using DeepSeek as main model")
    return get_deepseek_model()


def get_model() -> ChatOpenAI:
    """Alias for get_main_model() (backward compatibility)."""
    return get_main_model()


def get_structured_model(schema: Type[BaseModel]) -> StructuredModelWrapper:
    """Structured output with function_calling + JSON prompt fallback (Qwen thinking-safe)."""
    return StructuredModelWrapper(get_main_model(), schema)


def get_main_model_provider() -> str:
    """Get current main model provider name."""
    return os.getenv("MAIN_MODEL_PROVIDER", "deepseek")
