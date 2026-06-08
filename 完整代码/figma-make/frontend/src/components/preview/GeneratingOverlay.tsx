"use client";

import { FileCode2, Sparkles } from "lucide-react";
import { LabLoading } from "@/components/ui/LabLoading";

interface GeneratingOverlayProps {
  stepTitle: string;
  fileCount: number;
  recentFiles: string[];
  phase: "generating" | "assembling";
  /** code 视图只显示底部条，不遮挡文件树 */
  layout?: "full" | "compact";
}

export function GeneratingOverlay({
  stepTitle,
  fileCount,
  recentFiles,
  phase,
  layout = "full",
}: GeneratingOverlayProps) {
  const pulseKey = `${recentFiles[0] ?? ""}-${recentFiles.length}`;
  const message =
    phase === "assembling" ? "正在组装你的应用..." : "正在实时写入代码...";

  if (layout === "compact") {
    return (
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-40 border-t border-[var(--lab-green)]/20 bg-gradient-to-r from-white/95 via-[#fafff5]/95 to-[#fff8f0]/95 px-3 py-2 shadow-[0_-4px_20px_rgba(0,0,0,0.06)] backdrop-blur-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 shrink-0 animate-pulse text-[var(--lab-green-dark)]" />
            <span className="truncate text-xs font-medium text-gray-700">
              {stepTitle}
            </span>
            <span className="shrink-0 rounded-full bg-[#f4ffe8] px-2 py-0.5 text-[11px] font-medium text-[var(--lab-green-dark)]">
              {fileCount} 个文件
            </span>
          </div>
          {recentFiles[0] && (
            <div
              key={pulseKey}
              className="flex min-w-0 max-w-[45%] items-center gap-1.5 text-[11px] text-[var(--lab-orange)]"
            >
              <FileCode2 className="h-3 w-3 shrink-0" />
              <span className="truncate font-mono text-gray-600" title={recentFiles[0]}>
                {recentFiles[0]}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="pointer-events-none absolute inset-0 z-40 flex flex-col bg-gradient-to-br from-white/75 via-[#fafff5]/80 to-[#fff8f0]/80 backdrop-blur-[2px]">
      {/* 顶部进度条 */}
      <div className="h-1 w-full overflow-hidden bg-[var(--lab-border)]/40">
        <div className="h-full w-1/3 animate-pulse rounded-full bg-gradient-to-r from-transparent via-[var(--lab-green)] to-transparent" />
      </div>

      <div className="flex flex-1 items-end justify-between p-4">
        {/* 左下：当前步骤 */}
        <div className="max-w-[55%] rounded-xl border border-[var(--lab-green)]/25 bg-white/90 px-4 py-3 shadow-sm">
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-[var(--lab-green-dark)]">
            <Sparkles className="h-3.5 w-3.5 animate-pulse" />
            <span>{message}</span>
          </div>
          <div className="text-sm font-semibold text-gray-800">{stepTitle}</div>
          <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
            <span
              key={fileCount}
              className="inline-flex animate-in fade-in zoom-in-95 duration-300 rounded-full bg-[#f4ffe8] px-2 py-0.5 font-medium text-[var(--lab-green-dark)]"
            >
              已生成 {fileCount} 个文件
            </span>
          </div>
        </div>

        {/* 右下：最近文件 ticker */}
        {recentFiles.length > 0 && (
          <div
            key={pulseKey}
            className="max-w-[40%] animate-in slide-in-from-right-4 fade-in duration-500 rounded-xl border border-[var(--lab-orange)]/20 bg-white/90 px-3 py-2 shadow-sm"
          >
            <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-[var(--lab-orange)]">
              <FileCode2 className="h-3 w-3" />
              最新写入
            </div>
            <ul className="space-y-0.5">
              {recentFiles.slice(0, 4).map((file) => (
                <li
                  key={file}
                  className="truncate font-mono text-[11px] text-gray-600"
                  title={file}
                >
                  {file}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 中央轻量 loading（组装阶段更明显） */}
      {phase === "assembling" && (
        <div className="absolute inset-0 flex items-center justify-center">
          <LabLoading size="lg" message="化学反应进行中..." />
        </div>
      )}
    </div>
  );
}
