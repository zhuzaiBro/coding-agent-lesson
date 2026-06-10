"""
核心聊天接口（SSE 流式）。

请求链路：
1. 解析 mockConfig / projectId / existingFiles / useSupabase
2. resolve_route_adapter 分流 → traditional | figma | modification
3. agent.astream(stream_mode="updates") 逐节点推送 SSE
4. NODE_HANDLERS 将 LangGraph 节点名映射为前端事件类型（analysis、files 等）
"""
import json
import os
import random
import string
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from agents.graphs.main_graph import build_agent
from agents.adapters.route_registry import resolve_route_adapter
from agents.utils.model import get_main_model_provider
from config.mock import DEFAULT_MOCK_PRESET, MOCK_PRESETS, resolve_mock_config
from config.chat import NODE_HANDLERS


def _missing_model_key_message() -> str | None:
    provider = get_main_model_provider().lower()
    key_by_provider = {
        "deepseek": "DEEPSEEK_API_KEY",
        "glm": "GLM_API_KEY",
        "qwen": "QWEN_API_KEY",
    }
    key_name = key_by_provider.get(provider, "DEEPSEEK_API_KEY")
    if os.getenv(key_name, "").strip():
        return None
    return f"服务端未配置 {key_name}（当前 MAIN_MODEL_PROVIDER={provider}），请在服务器 .env 中填写后重启"

router = APIRouter()

# 在模块加载时预编译两套 Agent，避免每次请求都重新构建图（LangGraph 编译有一定耗时）
traditional_agent = build_agent("traditional")
figma_agent = build_agent("figma")
modification_agent = build_agent("modification")


@router.post("/")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    user_mock_config = body.get("mockConfig", None)
    project_id = body.get("projectId", None)

    print(f"Received messages count: {len(messages)}")

    # 解析 Mock 配置：仅 traditional 流程使用；figma 流程不支持逐节点 Mock
    # 请求未带 mockConfig 时：默认 allReal；仅当 MOCK_MODE=true 时回退为 allMock
    if user_mock_config is not None:
        mock_config_input = user_mock_config
    elif os.getenv("MOCK_MODE", "false").lower() == "true":
        mock_config_input = MOCK_PRESETS["allMock"].to_dict()
    else:
        mock_config_input = DEFAULT_MOCK_PRESET.to_dict()
    mock_config = resolve_mock_config(mock_config_input)

    existing_files = body.get("files") or body.get("existingFiles")

    # ========== 路由适配层：根据消息内容决定走哪条生成流程 ==========
    # 优先级：Figma URL(100) > 修改/迭代(90) > 图片附件(80) > 文本提示(70) > 兜底(10)
    use_supabase = body.get("useSupabase")
    if use_supabase is None:
        use_supabase = body.get("use_supabase")

    route_result = await resolve_route_adapter({
        "messages": messages,
        "mockConfig": mock_config,
        "existingFiles": existing_files,
        "files": existing_files,
        "useSupabase": use_supabase,
    })
    flow = route_result["flow"]

    if flow == "figma":
        print("[Route] Using Figma direct flow")
        if route_result.get("meta", {}).get("figmaUrl"):
            print(f"   URL: {route_result['meta']['figmaUrl']}")
    elif flow == "modification":
        file_count = len(existing_files) if isinstance(existing_files, dict) else 0
        print(f"[Route] Using Modification flow ({file_count} existing files)")
    else:
        print("[Route] Using Traditional flow")
        print(f"Using mockConfig: {json.dumps(mock_config)}")

    # thread_id 用于 LangGraph MemorySaver 实现会话级状态隔离
    # 同一 projectId 的请求共享同一条对话历史，支持多轮修改
    thread_id = project_id or f"project-{int(__import__('time').time() * 1000)}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=7))}"
    print(f"Using thread_id (projectId): {thread_id}")

    config = {"configurable": {"thread_id": thread_id}}
    if flow == "figma":
        agent = figma_agent
    elif flow == "modification":
        agent = modification_agent
    else:
        agent = traditional_agent
    input_data = route_result["input"]
    if use_supabase is not None and flow == "traditional":
        input_data = {**input_data, "useSupabase": bool(use_supabase)}

    async def event_generator():
        # 先发一个空注释包建立连接，部分浏览器/代理在收到第一条数据前不认为连接已就绪
        yield {"data": "", "event": "comment"}

        missing_key = _missing_model_key_message()
        if missing_key:
            yield {
                "data": json.dumps(
                    {"type": "error", "data": {"message": missing_key}}
                )
            }
            yield {"data": json.dumps({"type": "done"})}
            return

        try:
            # stream_mode="updates" 表示每个节点完成后立即推送该节点的 State 增量
            # 而不是等整条流水线结束才一次性返回，前端可实时显示每个步骤的进度
            async for chunk in agent.astream(input_data, config, stream_mode="updates"):
                print(f"Chunk received keys: {list(chunk.keys())}")

                node_name = list(chunk.keys())[0]
                output = chunk[node_name]

                if not output:
                    print(f"Empty output for node: {node_name}")
                    continue

                print(f"Processing node: {node_name}\n")

                # 通过 NODE_HANDLERS 将节点名映射为前端期望的 SSE 事件类型和数据字段
                # 例如：serviceNode → type="service", key="logic"（注意字段名是 logic 而非 service）
                handler = NODE_HANDLERS.get(node_name)
                if not handler:
                    print(f"Unknown node update: {node_name}")
                    continue

                event_type = handler["type"]
                payload = output.get(handler["key"])

                sse_message = json.dumps({"type": event_type, "data": payload})
                yield {"data": sse_message}

            # 所有节点执行完毕，通知前端关闭 SSE 连接
            yield {"data": json.dumps({"type": "done"})}

        except Exception as e:
            print(f"Error processing chat: {e}")
            yield {
                "data": json.dumps(
                    {
                        "type": "error",
                        "data": {"message": str(e), "nonBlocking": False},
                    }
                )
            }
            yield {"data": json.dumps({"type": "done"})}

    return EventSourceResponse(
        event_generator(),
        headers={
            # no-transform 防止 Nginx/CDN 对流式内容进行 gzip 压缩（压缩会破坏 SSE 实时性）
            "Cache-Control": "no-cache, no-transform",
            # 禁用 Nginx 等反向代理的响应缓冲，确保事件实时到达客户端
            "X-Accel-Buffering": "no",
        },
    )
