"""Structured output wrapper with Qwen/DeepSeek-compatible fallbacks."""
import json
import re
from typing import Any, List, Optional, Type

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from agents.shared.prompts.shared import JSON_SAFETY_PROMPT


def _extract_tool_call_args(tool_call: Any) -> Optional[Any]:
    if isinstance(tool_call, dict):
        args = tool_call.get("args")
        if args is not None:
            return args
        fn = tool_call.get("function")
        if isinstance(fn, dict):
            raw_args = fn.get("arguments")
            if isinstance(raw_args, str) and raw_args.strip():
                try:
                    return json.loads(raw_args)
                except json.JSONDecodeError:
                    return None
            return raw_args
        return None
    args = getattr(tool_call, "args", None)
    return args if args is not None else None


def _is_structured_format_unsupported(error: Exception) -> bool:
    msg = str(error).lower()
    return (
        "response_format" in msg
        or "json_schema" in msg
        or "function_call" in msg
        or "tool_choice" in msg
        or "thinking mode" in msg
        or "unavailable now" in msg
    )


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _loads_json_object(text: str) -> Optional[dict]:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group())
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


class StructuredModelWrapper:
    """Try function_calling/json_schema; fall back to JSON-in-prompt for Qwen thinking mode, etc."""

    STRUCTURED_METHODS = ("function_calling", "json_schema")

    def __init__(self, model: ChatOpenAI, schema: Type[BaseModel]):
        self._model = model
        self._schema = schema

    def _make_runnable(self, method: str) -> Any:
        return self._model.with_structured_output(
            self._schema,
            method=method,
            include_raw=True,
        )

    def _validate_payload(self, payload: Any) -> Optional[BaseModel]:
        if payload is None:
            return None
        if isinstance(payload, self._schema):
            return payload
        if not isinstance(payload, dict):
            return None
        try:
            return self._schema.model_validate(payload)
        except ValidationError as error:
            print(f"[Model] Schema validation failed: {error.errors()[:2]}")
            return None

    def _parse_structured_result(self, result: Any) -> Any:
        if isinstance(result, self._schema):
            return result

        if isinstance(result, dict):
            parsed = result.get("parsed")
            if parsed is not None:
                return parsed

            recovered = self._recover_from_raw(result)
            if recovered is not None:
                return recovered

            parsing_error = result.get("parsing_error")
            if parsing_error:
                raise ValueError(f"Structured model parsing failed: {parsing_error}")
            raise ValueError("Structured model returned None")

        if result is None:
            raise ValueError("Structured model returned None")

        validated = self._validate_payload(result)
        if validated is not None:
            return validated

        return result

    def _recover_from_content(self, raw: Any) -> Optional[BaseModel]:
        content = getattr(raw, "content", None)
        if content is None:
            return None

        if isinstance(content, list):
            parts: List[str] = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    parts.append(str(part.get("text", "")))
            content = "".join(parts)

        if not isinstance(content, str) or not content.strip():
            return None

        payload = _loads_json_object(_strip_json_fence(content))
        return self._validate_payload(payload)

    def _recover_from_raw(self, result: dict) -> Optional[BaseModel]:
        raw = result.get("raw")
        if raw is None:
            return None

        tool_calls = getattr(raw, "tool_calls", None) or []
        if not tool_calls:
            additional = getattr(raw, "additional_kwargs", None) or {}
            tool_calls = additional.get("tool_calls") or []

        for tool_call in tool_calls:
            args = _extract_tool_call_args(tool_call)
            if not args:
                continue
            if isinstance(args, str):
                args = _loads_json_object(_strip_json_fence(args))
                if args is None:
                    continue
            validated = self._validate_payload(args)
            if validated is not None:
                return validated

        return self._recover_from_content(raw)

    def _build_json_prompt_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        schema_json = json.dumps(
            self._schema.model_json_schema(),
            ensure_ascii=False,
            indent=2,
        )
        schema_block = (
            "\n\n【Structured JSON Output — Required】\n"
            "Respond with ONE raw JSON object only (no markdown fences, no commentary).\n"
            "The JSON must conform to this schema:\n"
            f"{schema_json}\n"
            f"{JSON_SAFETY_PROMPT}"
        )

        augmented: List[BaseMessage] = []
        injected = False
        for message in messages:
            if not injected and isinstance(message, SystemMessage):
                content = message.content
                if isinstance(content, str):
                    augmented.append(SystemMessage(content=content + schema_block))
                else:
                    augmented.append(message)
                    augmented.append(SystemMessage(content=schema_block.strip()))
                injected = True
            else:
                augmented.append(message)

        if not injected:
            augmented.insert(0, SystemMessage(content=schema_block.strip()))

        return augmented

    async def _ainvoke_json_prompt(self, messages: List[BaseMessage]) -> BaseModel:
        augmented = self._build_json_prompt_messages(messages)
        response = await self._model.ainvoke(augmented)
        parsed = self._recover_from_content(response)
        if parsed is None:
            raise ValueError("JSON prompt fallback could not parse model response")
        print("[Model] Structured output via json_prompt succeeded")
        return parsed

    async def ainvoke(self, messages: List[BaseMessage]) -> Any:
        last_error: Optional[Exception] = None
        skip_structured = False

        for method in self.STRUCTURED_METHODS:
            if skip_structured:
                break
            try:
                result = await self._make_runnable(method).ainvoke(messages)
                return self._parse_structured_result(result)
            except Exception as error:
                last_error = error if isinstance(error, Exception) else Exception(str(error))
                print(f"[Model] Structured output via {method} failed: {last_error}")
                if _is_structured_format_unsupported(last_error):
                    skip_structured = True

        try:
            return await self._ainvoke_json_prompt(messages)
        except Exception as fallback_error:
            print(f"[Model] JSON prompt fallback failed: {fallback_error}")

        raise last_error or ValueError("Structured model returned None")
