import type { StreamEventType } from "@/types/api";

const SUPABASE_TOOL_STEPS = new Set<StreamEventType>([
  "supabase",
  "inquiry",
  "chatReply",
]);

/** 是否为需要专用 Supabase UI 的思维链步骤 */
export function isSupabaseToolStep(type: StreamEventType): boolean {
  return SUPABASE_TOOL_STEPS.has(type);
}

/** 将 SSE data 挂到 ThoughtItem.payload */
export function supabaseThoughtPayload(
  type: StreamEventType,
  data: unknown,
): unknown | undefined {
  if (!isSupabaseToolStep(type)) return undefined;
  return data;
}
