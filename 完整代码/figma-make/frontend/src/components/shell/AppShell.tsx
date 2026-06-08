// 应用主壳层组件
"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { GitHubPixelAvatar } from "@/components/ui/GitHubPixelAvatar";
import { ChatPanel } from "./ChatPanel";
import { PreviewPanel } from "./PreviewPanel";
import { useSandpackStore } from "@/store/sandpackStore";
import { Eye, Code2, Settings, LogOut, Database } from "lucide-react";
import { FigmaHeaderConnectButton } from "@/components/integrations/FigmaConnectPanel";
import { SupabaseHeaderConnectButton } from "@/components/integrations/SupabaseConnectPanel";
import { useSupabaseConnect } from "@/hooks/useSupabaseConnect";
import type { LayoutMode, AppShellProps } from "@/types/components";

/**
 * AppShell
 *
 * 职责：
 * - 管理整体布局结构（两列 / 预览全屏）
 * - 分配 Chat / Preview 的空间
 *
 * 不负责：
 * - 不处理任何业务逻辑
 * - 不关心 prompt / sandpack / AI
 * - 不直接依赖 store（未来可由上层注入）
 */

export function AppShell({ children }: AppShellProps) {
  const { viewMode, setViewMode } = useSandpackStore();

  /**
   * 当前布局模式
   *
   * split         : Chat + Preview
   * preview-only  : Preview 全屏
   */
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("split");

  /**
   * 布局控制方法
   * 注意：这里只是能力，不是业务触发
   */
  const showPreviewOnly = () => setLayoutMode("preview-only");
  const showSplit = () => setLayoutMode("split");

  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { handleConnectClick } = useSupabaseConnect();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-[var(--background)]">
      {/* 顶部 Header */}
      <header className="relative z-[100] flex h-14 shrink-0 items-center justify-between overflow-visible border-b border-[var(--lab-border)] bg-gradient-to-r from-white via-[#fafff5] to-[#fff8f0] px-4 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2.5">
            <div className="relative h-9 w-9 shrink-0 overflow-hidden rounded-xl bg-[#f4ffe8] ring-1 ring-[var(--lab-green)]/30 shadow-sm">
              <Image
                src="/loading.gif"
                alt="Zood Figma Make"
                fill
                unoptimized
                className="object-contain p-0.5"
                sizes="36px"
              />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold text-gray-900">
                Zood{" "}
                <span className="text-[var(--lab-green-dark)]">Figma</span>{" "}
                Make
              </span>
              <span className="text-[10px] text-[var(--lab-text-muted)]">
                AI 实验室 · 从想法到应用
              </span>
            </div>
          </div>
        </div>

        {/* 中间 Toggle Controls */}
        <div className="absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2">
          <div className="flex items-center gap-1 rounded-lg border border-[var(--lab-border)] bg-[#f4ffe8] p-1">
            <button
              onClick={() => setViewMode("preview")}
              className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
                viewMode === "preview"
                  ? "bg-white text-gray-900 shadow-sm ring-1 ring-[var(--lab-green)]/40"
                  : "text-gray-500 hover:text-[var(--lab-green-dark)]"
              }`}
            >
              <Eye size={16} />
              预览
            </button>
            <button
              onClick={() => setViewMode("code")}
              className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-all ${
                viewMode === "code"
                  ? "bg-white text-gray-900 shadow-sm ring-1 ring-[var(--lab-orange)]/40"
                  : "text-gray-500 hover:text-[var(--lab-orange)]"
              }`}
            >
              <Code2 size={16} />
              代码
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <FigmaHeaderConnectButton />
          <SupabaseHeaderConnectButton />

        {/* 右侧 User Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-md border border-[#d0d7de] bg-[#f6f8fa] shadow-sm transition-all hover:border-[#2da44e]/50 hover:shadow-md active:scale-95"
            aria-label="用户菜单"
          >
            <GitHubPixelAvatar size={32} />
          </button>

          {isDropdownOpen && (
            <div className="absolute right-0 top-full z-[110] mt-2 w-48 origin-top-right animate-in fade-in zoom-in-95 duration-200 rounded-xl border border-[var(--lab-border)] bg-white p-1 shadow-lg ring-1 ring-[var(--lab-green)]/10 focus:outline-none">
              <button
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-[#f4ffe8] transition-colors"
                onClick={() => {
                  setIsDropdownOpen(false);
                  void handleConnectClick();
                }}
              >
                <Database size={16} className="text-[#1a7f4b]" />
                连接 Supabase
              </button>
              <button
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-[#f4ffe8] transition-colors"
                onClick={() => {
                  setIsDropdownOpen(false);
                }}
              >
                <Settings size={16} className="text-[var(--lab-green-dark)]" />
                设置
              </button>
              <button
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                onClick={() => {
                  console.log("Logout clicked");
                  setIsDropdownOpen(false);
                }}
              >
                <LogOut size={16} />
                退出登录
              </button>
            </div>
          )}
        </div>
        </div>
      </header>

      {/* 下方主体内容：包含 Chat 和 Preview */}
      <main className="relative z-0 flex flex-1 overflow-hidden gap-4 p-4">
        {/* 左侧 Chat 面板 */}
        <div
          className={`flex flex-col shrink-0 transition-all duration-300 ease-out ${
            layoutMode === "preview-only"
              ? "w-0 opacity-0 pointer-events-none"
              : "w-[400px] opacity-100"
          }`}
        >
          <div className="flex-1 min-h-0 overflow-hidden rounded-xl border border-[var(--lab-border)] bg-white shadow-sm ring-1 ring-[var(--lab-green)]/10">
            <ChatPanel />
          </div>
        </div>

        {/* 右侧 Preview 面板 */}
        <div className="flex-1 relative transition-all duration-300 ease-out">
          <PreviewPanel
            layoutMode={layoutMode}
            onExitFullScreen={showSplit}
            onEnterFullScreen={showPreviewOnly}
          >
            {children}
          </PreviewPanel>
        </div>
      </main>
    </div>
  );
}
