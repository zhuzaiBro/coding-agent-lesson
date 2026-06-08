// 预览工具栏组件
"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { useSandpackStore } from "@/store/sandpackStore";
import { downloadGeneratedCode } from "@/lib/downloadCode";
import { toast } from "sonner";
import type { PreviewToolbarProps } from "@/types/components";

/**
 * PreviewToolbar
 *
 * 职责：
 * - 提供 Preview 区域的布局控制（全屏 / 退出全屏）
 * - 提供代码下载功能
 *
 * 不负责：
 * - 不管理状态
 * - 不知道 Sandpack / Chat
 */
export function PreviewToolbar({
  isFullScreen,
  onEnterFullScreen,
  onExitFullScreen,
}: PreviewToolbarProps) {
  const {
    generatedFiles,
    viewMode,
    isGenerating,
    generatedFileCount,
    generationStepTitle,
  } = useSandpackStore();
  const [isDownloading, setIsDownloading] = useState(false);

  // 从全局获取 templateFiles（由 SandpackView 设置）
  const templateFiles =
    typeof window !== "undefined" ? window.__templateFiles || {} : {};
  const hasDownloadableFiles =
    generatedFiles || Object.keys(templateFiles).length > 0;

  const handleDownload = async () => {
    if (!hasDownloadableFiles) {
      toast.error("暂无可下载的代码");
      return;
    }

    setIsDownloading(true);
    try {
      // 如果没有生成代码，就只下载模板代码
      const filesToDownload = generatedFiles || templateFiles;
      await downloadGeneratedCode(filesToDownload, templateFiles);
      toast.success("代码下载成功");
    } catch (error) {
      console.error("下载失败:", error);
      toast.error("下载失败，请重试");
    } finally {
      setIsDownloading(false);
    }
  };

  const isDownloadDisabled = !hasDownloadableFiles || isDownloading;

  return (
    <div className="flex items-center gap-2">
      {isGenerating && (
        <div className="flex items-center gap-1.5 rounded-full border border-[var(--lab-green)]/30 bg-[#f4ffe8]/90 px-2.5 py-1 text-[11px] font-medium text-[var(--lab-green-dark)] shadow-sm">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--lab-green)] opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[var(--lab-green)]" />
          </span>
          <span className="max-w-[120px] truncate">{generationStepTitle}</span>
          <span className="text-[var(--lab-green-dark)]/70">· {generatedFileCount} 文件</span>
        </div>
      )}

      {/* 下载代码按钮 - 只在代码视图显示 */}
      {viewMode === "code" && (
        <button
          type="button"
          onClick={handleDownload}
          disabled={isDownloadDisabled}
          className="flex items-center gap-1.5 rounded-md border border-[var(--lab-border)] bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:bg-[#f4ffe8] hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-white"
          title={!hasDownloadableFiles ? "正在加载模板..." : "下载代码"}
        >
          <Download className="h-3.5 w-3.5" />
          {isDownloading ? "下载中..." : "下载代码"}
        </button>
      )}

      {!isFullScreen && (
        <button
          type="button"
          onClick={onEnterFullScreen}
          className="rounded-md border border-[var(--lab-border)] bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:bg-[#fff5eb] hover:text-[var(--lab-orange)]"
        >
          全屏
        </button>
      )}

      {isFullScreen && (
        <button
          type="button"
          onClick={onExitFullScreen}
          className="rounded-md border border-[var(--lab-border)] bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:bg-[#f4ffe8] hover:text-[var(--lab-green-dark)]"
        >
          退出全屏
        </button>
      )}
    </div>
  );
}
