/** 与后端 intent_helpers.TRIVIAL_CHIT_CHAT 对齐的简短寒暄检测 */
const TRIVIAL_CHIT_CHAT = new Set([
  "hi",
  "hello",
  "hey",
  "yo",
  "hola",
  "你好",
  "您好",
  "在吗",
  "哈喽",
  "嗨",
]);

export function isTrivialChitChatMessage(text: string): boolean {
  const normalized = text.trim().toLowerCase().replace(/[!！?？.]+$/g, "");
  if (!normalized) return false;
  if (TRIVIAL_CHIT_CHAT.has(normalized)) return true;
  return normalized.length <= 4 && /^[a-z]+$/.test(normalized);
}

function normalizeIntentType(type: unknown): string {
  if (type == null) return "";
  if (typeof type === "string") return type;
  if (typeof type === "object" && type !== null && "value" in type) {
    return String((type as { value: unknown }).value);
  }
  return String(type);
}

/** analysis SSE data 是否为数据库探查问答（走 inquiry 分支，不跑代码生成） */
export function isDatabaseInquiryAnalysis(data: unknown): boolean {
  if (!data || typeof data !== "object") return false;
  const d = data as Record<string, unknown>;
  const typeStr = normalizeIntentType(d.type);
  return typeStr.includes("QA") && d.needsDatabase === true;
}

/** analysis SSE data 是否为闲聊/问答（走 conversationalReply，不跑生成流水线） */
export function isConversationalAnalysis(data: unknown): boolean {
  if (isDatabaseInquiryAnalysis(data)) return false;
  if (!data || typeof data !== "object") return false;
  const d = data as Record<string, unknown>;
  const typeStr = normalizeIntentType(d.type);
  if (typeStr === "CHIT_CHAT" || typeStr === "QA") return true;
  if (typeStr.includes("CHIT_CHAT") || typeStr.includes("QA")) return true;
  const tags = d.tags;
  if (Array.isArray(tags)) {
    if (tags.includes("闲聊") || tags.includes("问答")) return true;
  }
  return false;
}

export function conversationalAnalysisDescription(data: unknown): string {
  if (isDatabaseInquiryAnalysis(data)) {
    const reason = (data as Record<string, unknown>).databaseReason;
    return typeof reason === "string" && reason
      ? `需要查库分析：${reason}`
      : "需要连接数据库探查真实数据";
  }
  const typeStr = normalizeIntentType(
    data && typeof data === "object"
      ? (data as Record<string, unknown>).type
      : undefined,
  );
  if (typeStr.includes("CHIT_CHAT")) {
    return "识别为闲聊，将直接对话回复。";
  }
  if (typeStr.includes("QA")) {
    return "识别为问答，将直接对话回复。";
  }
  return "需求拆解完成，核心场景已确认。";
}
