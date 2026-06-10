"use client";

import { useRef } from "react";
import { Database } from "lucide-react";
import { useSupabaseConnect } from "@/hooks/useSupabaseConnect";

/** 点击打开 Supabase 浏览器授权页 */
export function SupabaseConnectButton({
  onToast,
}: {
  onToast?: (message: string, type?: "info" | "warning" | "error") => void;
}) {
  const {
    enabled,
    linked,
    connectionState,
    isConnecting,
    handleConnectClick,
  } = useSupabaseConnect(onToast);

  const statusDot =
    linked && enabled
      ? "bg-emerald-500"
      : isConnecting
        ? "bg-amber-400 animate-pulse"
        : connectionState === "error"
          ? "bg-red-500"
          : "bg-gray-300";

  return (
    <button
      type="button"
      title={
        linked && enabled
          ? "已连接（点击断开）"
          : "在浏览器中连接 Supabase"
      }
      disabled={isConnecting}
      onClick={() => void handleConnectClick()}
      className={`relative shrink-0 rounded-md p-1.5 text-sm transition-colors disabled:opacity-60 ${
        linked && enabled
          ? "bg-[#3ecf8e]/15 text-[#1a7f4b] ring-1 ring-[#3ecf8e]/40"
          : "text-gray-500 hover:bg-gray-100 hover:text-gray-800"
      }`}
    >
      <Database
        size={18}
        className={isConnecting ? "animate-pulse" : undefined}
      />
      <span className="sr-only">
        {linked && enabled ? "Supabase 已连接" : "连接 Supabase"}
      </span>
      <span
        className={`absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full ${statusDot}`}
      />
    </button>
  );
}

/** 顶栏用：与聊天区相同的授权按钮 */
export function SupabaseHeaderConnectButton({
  onToast,
}: {
  onToast?: (message: string, type?: "info" | "warning" | "error") => void;
}) {
  const wrapRef = useRef<HTMLButtonElement>(null);
  const {
    enabled,
    linked,
    isConnecting,
    handleConnectClick,
  } = useSupabaseConnect(onToast);

  return (
    <button
      ref={wrapRef}
      type="button"
      disabled={isConnecting}
      title={
        linked && enabled
          ? "Supabase 已连接（点击断开）"
          : "在浏览器中连接 Supabase"
      }
      onClick={() => void handleConnectClick()}
      className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all disabled:opacity-60 ${
        linked && enabled
          ? "border-[#3ecf8e]/50 bg-[#3ecf8e]/10 text-[#1a7f4b]"
          : "border-[var(--lab-border)] bg-white text-gray-600 hover:bg-[#f4ffe8]"
      }`}
    >
      <Database
        size={16}
        className={isConnecting ? "animate-pulse" : undefined}
      />
      {linked && enabled ? "已连接" : "Supabase"}
    </button>
  );
}
