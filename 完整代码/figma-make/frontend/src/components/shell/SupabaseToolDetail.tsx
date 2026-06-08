"use client";

import type { ReactNode } from "react";
import { Database } from "lucide-react";
import { McpToolRunCard } from "@/components/shell/McpToolRunCard";
import type {
  ChatReplyPayload,
  InquiryPayload,
  InquiryTraceItem,
  SupabaseContextPayload,
} from "@/types/supabaseTool";

const SUPABASE_GREEN = "#3ecf8e";

/** supabase 子图 → 多个 MCP 工具卡片 */
function SupabaseContextDetail({ data }: { data: SupabaseContextPayload }) {
  const connected = data.enabled !== false && !data.error;
  const schema = data.schemaSummary?.trim() ?? "";
  const cards: ReactNode[] = [];

  cards.push(
    <McpToolRunCard
      key="connect"
      toolName="Connect"
      params={[
        {
          key: "mcp",
          value: "https://mcp.supabase.com/mcp",
          copyable: true,
        },
      ]}
      result={
        connected
          ? {
              ok: true,
              projectUrl: data.projectUrl ?? null,
              readOnly: data.readOnly !== false,
            }
          : { ok: false, error: data.error ?? "connection failed" }
      }
      error={data.error}
      defaultOpen
    />,
  );

  if (connected && data.projectUrl) {
    cards.push(
      <McpToolRunCard
        key="project-url"
        toolName="Get Project Url"
        result={{ projectUrl: data.projectUrl }}
        defaultOpen={false}
      />,
    );
  }

  if (connected && schema) {
    cards.push(
      <McpToolRunCard
        key="list-tables"
        toolName="List Tables"
        params={[
          { key: "schemas", value: '["public"]' },
          { key: "verbose", value: "true" },
        ]}
        result={{ schema: schema }}
        defaultOpen={schema.length < 400}
      />,
    );
  }

  if (data.typescriptTypes?.trim()) {
    cards.push(
      <McpToolRunCard
        key="gen-types"
        toolName="Generate Typescript Types"
        result={{ types: data.typescriptTypes.slice(0, 8000) }}
        defaultOpen={false}
      />,
    );
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
        <Database className="h-3 w-3" style={{ color: SUPABASE_GREEN }} />
        Supabase MCP · {cards.length} tool{cards.length > 1 ? "s" : ""}
      </div>
      {cards}
    </div>
  );
}

function traceToMcpCard(item: InquiryTraceItem, index: number) {
  const status = item.status ?? "ok";

  if (status === "rejected") {
    return (
      <McpToolRunCard
        key={`sql-${item.round ?? index}`}
        toolName="Execute Sql"
        params={item.sql ? [{ key: "query", value: item.sql }] : []}
        result={{ rejected: true, reason: item.reason ?? "read-only guard" }}
        defaultOpen
      />
    );
  }

  if (status === "error") {
    return (
      <McpToolRunCard
        key={`sql-${item.round ?? index}`}
        toolName="Execute Sql"
        params={item.sql ? [{ key: "query", value: item.sql }] : []}
        error={item.error ?? "query failed"}
        defaultOpen
      />
    );
  }

  return (
    <McpToolRunCard
      key={`sql-${item.round ?? index}`}
      toolName="Execute Sql"
      params={item.sql ? [{ key: "query", value: item.sql }] : []}
      result={item.resultPreview ?? ""}
      showUntrustedWarning
      defaultOpen={index === 0}
    />
  );
}

function InquiryDetail({ data }: { data: InquiryPayload }) {
  const trace = data.trace ?? [];

  return (
    <div className="mt-2 space-y-2">
      {data.question && (
        <p className="text-[11px] text-zinc-500 px-0.5">
          <span className="text-zinc-600 font-medium">Question · </span>
          {data.question}
        </p>
      )}

      {trace.length > 0 ? (
        <>
          <div className="text-[10px] font-medium uppercase tracking-wider text-zinc-500 px-0.5">
            {trace.length} MCP tool run{trace.length > 1 ? "s" : ""}
          </div>
          {trace.map((item, i) => traceToMcpCard(item, i))}
        </>
      ) : data.status === "error" ? (
        <McpToolRunCard
          toolName="Execute Sql"
          error={data.message ?? "inquiry failed"}
          defaultOpen
        />
      ) : null}

      {data.message && data.status !== "error" && (
        <div
          className="rounded-lg border border-zinc-700/60 bg-zinc-900/90 px-3 py-2.5 text-[13px] text-zinc-200 leading-relaxed"
          style={{ borderColor: `${SUPABASE_GREEN}33` }}
        >
          <div
            className="mb-1 text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: SUPABASE_GREEN }}
          >
            Analysis
          </div>
          <p className="whitespace-pre-wrap">{data.message}</p>
        </div>
      )}
    </div>
  );
}

function ChatReplyDetail({ data }: { data: ChatReplyPayload }) {
  const text = data.message ?? data.inquiry?.message;
  if (!text) return null;

  const fromDb = Boolean(data.inquiry);
  const trace = data.inquiry?.trace ?? [];

  return (
    <div className="mt-2 space-y-2">
      {fromDb && trace.length > 0 && (
        <p className="text-[10px] text-zinc-500">
          {trace.length} tool run(s) above · conclusion below
        </p>
      )}
      <div className="rounded-lg border border-zinc-700/60 bg-zinc-950 px-3 py-2.5">
        {fromDb && (
          <div
            className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: SUPABASE_GREEN }}
          >
            <Database className="h-3 w-3" />
            Final answer
          </div>
        )}
        <p className="text-[13px] text-zinc-200 leading-relaxed whitespace-pre-wrap">
          {text}
        </p>
      </div>
    </div>
  );
}

export type SupabaseToolStep = "supabase" | "inquiry" | "chatReply";

export function SupabaseToolDetail({
  step,
  data,
}: {
  step: SupabaseToolStep;
  data: unknown;
}) {
  if (!data || typeof data !== "object") return null;

  if (step === "supabase") {
    return <SupabaseContextDetail data={data as SupabaseContextPayload} />;
  }
  if (step === "inquiry") {
    return <InquiryDetail data={data as InquiryPayload} />;
  }
  if (step === "chatReply") {
    return <ChatReplyDetail data={data as ChatReplyPayload} />;
  }
  return null;
}
