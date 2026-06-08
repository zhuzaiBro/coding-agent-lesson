/** Supabase MCP 子图输出 */
export interface SupabaseContextPayload {
  enabled?: boolean;
  projectUrl?: string;
  publishableKeyHint?: boolean;
  schemaSummary?: string;
  typescriptTypes?: string;
  readOnly?: boolean;
  error?: string;
}

/** 单轮 SQL 探查记录 */
export interface InquiryTraceItem {
  round?: number;
  sql?: string;
  status?: "ok" | "error" | "rejected";
  resultPreview?: string;
  error?: string;
  reason?: string;
  truncated?: boolean;
}

/** 数据库探查节点输出 */
export interface InquiryPayload {
  status?: "ok" | "error" | "max_rounds";
  question?: string;
  message?: string;
  trace?: InquiryTraceItem[];
  rounds?: number;
}

/** chatReply 携带的探查结论 */
export interface ChatReplyPayload {
  message?: string;
  inquiry?: InquiryPayload;
}
