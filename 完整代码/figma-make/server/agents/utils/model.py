"""
多模型统一入口（LangChain ChatOpenAI 兼容接口）。

主模型（代码生成 / 结构化输出）：
- DeepSeek（默认）
- 智谱 GLM
- 通义 Qwen 文本模型

视觉模型（仅图片分析）：
- Qwen-VL

通过环境变量 MAIN_MODEL_PROVIDER=deepseek|glm|qwen 切换主模型。
各模型实例单例缓存，避免重复创建连接。
"""
import os
from typing import Optional, Type

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from agents.utils.structured_model import StructuredModelWrapper

# 单例实例缓存
_deepseek_instance: Optional[ChatOpenAI] = None
_glm_instance: Optional[ChatOpenAI] = None
_qwen_text_instance: Optional[ChatOpenAI] = None
_qwen_vision_instance: Optional[ChatOpenAI] = None


def get_deepseek_model() -> ChatOpenAI:
    """获取 DeepSeek 主模型实例。"""
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
    """获取智谱 GLM 主模型实例。"""
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
    """解析用于结构化输出 / function calling 的 Qwen 文本模型。"""
    explicit = os.getenv("QWEN_TEXT_MODEL")
    if explicit:
        return explicit

    legacy = os.getenv("QWEN_MODEL")
    if legacy and "vl" not in legacy.lower():
        return legacy

    return "qwen-plus"


def _resolve_qwen_vision_model() -> str:
    """解析用于图片分析的 Qwen 视觉模型。"""
    return os.getenv("QWEN_VL_MODEL") or os.getenv("QWEN_MODEL") or "qwen-vl-max"


def _qwen_extra_body() -> dict:
    """DashScope：关闭 thinking 模式以支持 function_calling / tool_choice。"""
    enable = os.getenv("QWEN_ENABLE_THINKING", "false").lower() in ("1", "true", "yes")
    return {"enable_thinking": enable}


def get_qwen_model() -> ChatOpenAI:
    """获取 Qwen 文本主模型（DashScope 兼容模式 API）。"""
    global _qwen_text_instance
    if _qwen_text_instance is None:
        model = _resolve_qwen_text_model()
        if "vl" in model.lower():
            print(
                f"[Model] 警告: Qwen 文本模型 '{model}' 看起来像视觉模型。"
                "代码生成请设置 QWEN_TEXT_MODEL=qwen-plus 或 qwen-max。"
            )
        thinking = _qwen_extra_body().get("enable_thinking")
        if thinking:
            print(
                "[Model] 警告: QWEN_ENABLE_THINKING=true — 结构化输出可能失败，"
                "将回退到 JSON prompt 模式。"
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
    """获取 Qwen-VL 视觉模型实例（仅用于图片分析）。"""
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
    """根据 MAIN_MODEL_PROVIDER 环境变量获取当前配置的主模型。"""
    provider = os.getenv("MAIN_MODEL_PROVIDER", "deepseek").lower()

    if provider == "glm":
        print("[Model] 使用 GLM 作为主模型")
        return get_glm_model()
    if provider == "qwen":
        print(f"[Model] 使用 Qwen 作为主模型 ({_resolve_qwen_text_model()})")
        return get_qwen_model()
    print("[Model] 使用 DeepSeek 作为主模型")
    return get_deepseek_model()


def get_model() -> ChatOpenAI:
    """get_main_model() 的别名（向后兼容）。"""
    return get_main_model()


def get_structured_model(schema: Type[BaseModel]) -> StructuredModelWrapper:
    """结构化输出：function_calling + JSON prompt 回退（兼容 Qwen thinking 模式）。"""
    return StructuredModelWrapper(get_main_model(), schema)


def get_main_model_provider() -> str:
    """获取当前主模型提供商名称。"""
    return os.getenv("MAIN_MODEL_PROVIDER", "deepseek")
