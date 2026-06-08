// Sandpack 代码预览组件
"use client";

import {
  SandpackLayout,
  SandpackPreview,
  SandpackCodeEditor,
  SandpackFileExplorer,
  useSandpack,
  useActiveCode,
} from "@codesandbox/sandpack-react";
import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useSandpackStore } from "@/store/sandpackStore";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { getReactTS_Template } from "@/services/api";
import {
  getSandpackActiveFile,
  getSandpackVisibleFiles,
  mergeSandpackFiles,
} from "@/lib/mergeSandpackFiles";
import { getSandpackCustomSetup } from "@/lib/sandpackSetup";
import { LabLoading } from "@/components/ui/LabLoading";
import { GeneratingOverlay } from "./GeneratingOverlay";
import { SandpackErrorOverlay } from "./SandpackErrorOverlay";
import { SandpackFilesSync } from "./SandpackFilesSync";
import { SandpackPreviewBridge } from "./SandpackPreviewBridge";

// Client-only provider to prevent hydration mismatch
const SandpackProvider = dynamic(
  () =>
    import("@codesandbox/sandpack-react").then((mod) => mod.SandpackProvider),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#f4ffe8] to-[#fff5eb]">
        <LabLoading size="md" message="初始化预览环境..." />
      </div>
    ),
  },
);

export function SandpackView() {
  const {
    viewMode,
    generatedFiles,
    isAssembling,
    isGenerating,
    generationSessionId,
    generationStepTitle,
    generatedFileCount,
    recentFiles,
    previewReadyKey,
    setIsAssembling,
  } = useSandpackStore();
  const [templateFiles, setTemplateFiles] = useState<
    Record<string, { code: string }>
  >({});
  const [loading, setLoading] = useState(true);

  // 将 templateFiles 暴露给全局（供 PreviewToolbar 使用）
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.__templateFiles = templateFiles;
    }
  }, [templateFiles]);

  // 加载默认模板
  useEffect(() => {
    async function load() {
      try {
        const template = await getReactTS_Template();
        setTemplateFiles(template);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // 合并模板 + 生成文件，并镜像到 /src/ 供 Sandpack 入口使用
  const files = useMemo(
    () => mergeSandpackFiles(templateFiles, generatedFiles),
    [templateFiles, generatedFiles],
  );

  const sandpackKey = `${generationSessionId ?? "template"}-${previewReadyKey}-${generatedFileCount}`;

  const showGeneratingOverlay = isGenerating || isAssembling;

  if (loading) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#f4ffe8] to-[#fff5eb]">
        <LabLoading size="md" message="正在加载 React 模板..." />
      </div>
    );
  }

  const visibleFiles = getSandpackVisibleFiles(generatedFiles);
  const activeFile = getSandpackActiveFile(generatedFiles);
  const customSetup = getSandpackCustomSetup(generatedFiles);

  return (
    <SandpackProvider
      key={sandpackKey}
      template="vite-react-ts"
      theme="light"
      files={files}
      options={{
        externalResources: ["https://cdn.tailwindcss.com"],
        visibleFiles,
        activeFile,
        startRoute: "/",
        autorun: true,
        autoReload: true,
        recompileMode: "immediate",
      }}
      customSetup={customSetup}
      style={{ height: "100%", width: "100%" }}
    >
      <SandpackFilesSync templateFiles={templateFiles} />
      <SandpackPreviewBridge />
      <div className="relative h-full w-full border-none sandpack-wrapper">
        <SandpackErrorOverlay />
        {showGeneratingOverlay && (
          <GeneratingOverlay
            stepTitle={generationStepTitle}
            fileCount={generatedFileCount}
            recentFiles={recentFiles}
            phase={isAssembling ? "assembling" : "generating"}
            layout={viewMode === "code" && !isAssembling ? "compact" : "full"}
          />
        )}

        <SandpackLayout
          style={{ height: "100%", border: "none", borderRadius: 0 }}
        >
          <SandpackContent
            viewMode={viewMode}
            onReady={() => {
              if (isAssembling) {
                setIsAssembling(false);
              }
            }}
          />
        </SandpackLayout>
      </div>
    </SandpackProvider>
  );
}

function SandpackContent({
  viewMode,
  onReady,
}: {
  viewMode: "preview" | "code";
  onReady?: () => void;
}) {
  const { sandpack } = useSandpack();
  const { code } = useActiveCode();
  const { previewReadyKey } = useSandpackStore();
  const lastPreviewCode = useRef<string | undefined>(code);
  const pendingRefresh = useRef(false);
  const [isFileTreeOpen, setIsFileTreeOpen] = useState(true);
  const sandpackRef = useRef(sandpack);
  const hasNotifiedReady = useRef(false);

  useEffect(() => {
    sandpackRef.current = sandpack;
  }, [sandpack]);

  useEffect(() => {
    hasNotifiedReady.current = false;
  }, [previewReadyKey]);

  // 生成完成后强制刷新预览
  useEffect(() => {
    if (previewReadyKey <= 0) return;
    sandpackRef.current.runSandpack();
    const retry = setTimeout(() => sandpackRef.current.runSandpack(), 600);
    return () => clearTimeout(retry);
  }, [previewReadyKey]);

  // 流式写入由 SandpackFilesSync 防抖触发 runSandpack，此处不再重复调用以免主线程卡死

  // ✨ 监听 Sandpack 预览 iframe 加载完成
  useEffect(() => {
    if (!onReady) return;

    const notifyReady = () => {
      if (hasNotifiedReady.current) return;
      hasNotifiedReady.current = true;
      onReady();
    };

    const tryAttach = () => {
      const iframe =
        document.querySelector<HTMLIFrameElement>(".sp-preview-iframe");
      if (!iframe) return false;

      try {
        if (iframe.contentDocument?.readyState === "complete") {
          notifyReady();
          return true;
        }
      } catch {
        // 跨域或访问异常时，等待 load 事件
      }

      const handleLoad = () => {
        notifyReady();
      };
      iframe.addEventListener("load", handleLoad, { once: true });
      return true;
    };

    let intervalId: number | undefined;
    if (!tryAttach()) {
      intervalId = window.setInterval(() => {
        if (tryAttach() && intervalId) {
          window.clearInterval(intervalId);
        }
      }, 200);
    }

    return () => {
      if (intervalId) window.clearInterval(intervalId);
    };
  }, [onReady]);

  // 限制 tab 数量
  const MAX_TABS = 4;
  const prevVisibleFilesRef = useRef<string[]>([]);

  useEffect(() => {
    const visibleFiles = sandpack.visibleFiles;
    if (visibleFiles.length <= MAX_TABS) {
      prevVisibleFilesRef.current = visibleFiles;
      return;
    }

    const prevLen = prevVisibleFilesRef.current.length;
    if (visibleFiles.length <= prevLen) {
      prevVisibleFilesRef.current = visibleFiles;
      return;
    }

    const activeFile = sandpack.activeFile;
    const fileToClose = visibleFiles.find((f) => f !== activeFile);
    if (fileToClose) {
      sandpackRef.current.closeFile(fileToClose);
    }

    prevVisibleFilesRef.current = visibleFiles;
  }, [sandpack.visibleFiles, sandpack.activeFile]);

  useEffect(() => {
    if (viewMode === "code" && code !== lastPreviewCode.current) {
      pendingRefresh.current = true;
    }
  }, [code, viewMode]);

  useEffect(() => {
    if (viewMode !== "preview") {
      return;
    }

    if (pendingRefresh.current) {
      sandpackRef.current.runSandpack();
      pendingRefresh.current = false;
    }

    lastPreviewCode.current = code;
  }, [viewMode, code]);

  return (
    <div className="relative h-full w-full bg-white">
      <div
        className={viewMode === "preview" ? "h-full" : "hidden"}
        aria-hidden={viewMode !== "preview"}
      >
        <SandpackPreview
          style={{ height: "100%" }}
          showNavigator
          showOpenInCodeSandbox={false}
          showRefreshButton={true}
          startRoute="/"
        />
      </div>
      <div
        className={viewMode === "code" ? "h-full" : "hidden"}
        aria-hidden={viewMode !== "code"}
      >
        <div className="relative flex h-full w-full overflow-hidden">
          <div
            className={`relative flex-shrink-0 h-full flex-col border-r border-gray-200 overflow-hidden transition-all duration-300 ease-in-out ${
              isFileTreeOpen ? "w-[200px]" : "w-0 border-none"
            }`}
          >
            <div
              className={`h-full w-full overflow-y-auto transition-opacity duration-300 ${
                isFileTreeOpen ? "opacity-100" : "opacity-0"
              }`}
            >
              <SandpackFileExplorer style={{ height: "auto", width: "100%" }} />
            </div>
          </div>

          {/* 编辑器容器 */}
          <div className="relative flex-1 h-full min-w-0 overflow-hidden">
            <SandpackCodeEditor
              style={{ height: "100%", width: "100%" }}
              showTabs={true}
              showLineNumbers={true}
              showInlineErrors={true}
              wrapContent={true}
              closableTabs={true}
            />
          </div>

          {/* Toggle Button Overlaid on the Divider line */}
          <button
            type="button"
            onClick={() => setIsFileTreeOpen((prev) => !prev)}
            className={`absolute top-7 z-20 flex h-6 w-6 items-center justify-center border border-gray-200 bg-white text-gray-500 shadow-sm hover:text-gray-700 transition-all duration-300 ${
              isFileTreeOpen
                ? "rounded-full"
                : "rounded-r-full rounded-l-none border-l-0"
            }`}
            style={{
              left: isFileTreeOpen ? 200 : 0,
              transform: isFileTreeOpen ? "translateX(-50%)" : "translateX(0)",
            }}
            aria-label={
              isFileTreeOpen ? "Collapse file tree" : "Expand file tree"
            }
          >
            {isFileTreeOpen ? (
              <ChevronLeft size={14} />
            ) : (
              <ChevronRight size={14} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
