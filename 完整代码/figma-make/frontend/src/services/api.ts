// API 请求封装
import { API_BASE_URL } from "@/constants/config";
import { ChatMessage } from "@/types/message";
import { StreamEvent } from "@/types/api";

export async function getReactTS_Template(): Promise<
  Record<string, { code: string }>
> {
  const response = await fetch(`${API_BASE_URL}/api/template/react-ts`);
  if (!response.ok) {
    throw new Error("Failed to fetch template");
  }
  return response.json();
}

/** 从单个 SSE 块中提取并拼接 data 字段（支持多行 data:） */
function extractSseData(block: string): string | null {
  const trimmed = block.trim();
  if (!trimmed || trimmed.startsWith(":")) return null;

  const dataLines = trimmed
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).replace(/^\s/, ""));

  if (dataLines.length === 0) return null;
  return dataLines.join("\n").trim();
}

/** 解析 buffer 中完整的 SSE 块，返回剩余未完成的 buffer */
function parseSseBuffer(
  buffer: string,
  onChunk: (event: StreamEvent) => void,
  flush = false,
): string {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const blocks = normalized.split("\n\n");

  if (!flush) {
    buffer = blocks.pop() || "";
  } else {
    buffer = "";
  }

  for (const block of blocks) {
    const jsonStr = extractSseData(block);
    if (!jsonStr) continue;

    try {
      const raw = JSON.parse(jsonStr) as StreamEvent & {
        message?: string;
        nonBlocking?: boolean;
      };
      const event: StreamEvent =
        raw.type === "error" && raw.data === undefined
          ? {
              type: "error",
              data: {
                message: raw.message ?? "未知错误",
                nonBlocking: raw.nonBlocking,
              },
            }
          : raw;
      console.log("[Stream] Parsed event:", event.type);
      onChunk(event);
    } catch (e) {
      console.warn("Failed to parse SSE message:", jsonStr.slice(0, 120), e);
    }
  }

  return buffer;
}

/**
 * generateApp (Stream)
 *
 * 调用后端 /api/chat 接口 (SSE模式)
 * 职责：
 * - 发送对话上下文和项目 ID
 * - 处理 SSE 流式响应，回调 onChunk 更新状态
 */
export async function generateAppStream(
  params: {
    messages: ChatMessage[];
    projectId?: string;
    /** 编辑已生成应用时传入当前 Sandpack 文件（path → code） */
    files?: Record<string, string>;
    /** 显式启用 Supabase MCP 上下文（也可由服务端根据关键词推断） */
    useSupabase?: boolean;
    /** 多轮对话压缩摘要（与服务端 checkpoint 同步） */
    conversationSummary?: string | null;
  },
  onChunk: (event: StreamEvent) => void,
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        messages: params.messages,
        projectId: params.projectId,
        ...(params.files && Object.keys(params.files).length > 0
          ? { files: params.files }
          : {}),
        ...(params.useSupabase ? { useSupabase: true } : {}),
        ...(params.conversationSummary
          ? { conversationSummary: params.conversationSummary }
          : {}),
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }

    if (!response.body) {
      throw new Error("No response body");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      buffer = parseSseBuffer(buffer, onChunk);
    }

    // 流结束时 flush 剩余 buffer（最后一条可能没有 \n\n 结尾）
    parseSseBuffer(buffer, onChunk, true);
  } catch (error) {
    console.error("Stream error:", error);
    onChunk({
      type: "error",
      data: {
        message: error instanceof Error ? error.message : "Network error",
      },
    });
  }
}

/**
 * generateApp (Legacy) - 已废弃，提醒迁移
 */
export async function generateApp(): Promise<{ message: string }> {
  throw new Error("generateApp is deprecated. Use generateAppStream instead.");
}
