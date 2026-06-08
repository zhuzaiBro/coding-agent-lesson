import { create } from "zustand";
import type { SandpackStore, SandpackFiles } from "@/types/store";

// Re-export types for backward compatibility
export type { SandpackFiles };

type RawFileValue = string | { code?: unknown };

function normalizeCode(value: RawFileValue): string {
  if (typeof value === "string") return value;
  return typeof value.code === "string" ? value.code : "";
}

function toSandpackFiles(files: Record<string, RawFileValue>): SandpackFiles {
  const sandpackFiles: SandpackFiles = {};
  Object.entries(files).forEach(([path, value]) => {
    sandpackFiles[path] = { code: normalizeCode(value) };
  });
  return sandpackFiles;
}

export const useSandpackStore = create<SandpackStore>((set) => ({
  viewMode: "preview",
  setViewMode: (mode) => set({ viewMode: mode }),

  generatedFiles: null,
  setGeneratedFiles: (files) => {
    const sandpackFiles = toSandpackFiles(files);
    set((state) => ({
      generatedFiles: sandpackFiles,
      generatedFileCount: Object.keys(sandpackFiles).length,
      recentFiles: Object.keys(sandpackFiles).slice(-5).reverse(),
      filesRevision: state.filesRevision + 1,
    }));
  },
  /**
   * 全量 files 事件：更新文件；仅在编译检查结束后 remount 预览（避免 assemble/postProcess 三次重建）。
   */
  applyAssembledFiles: (files, options) => {
    const sandpackFiles = toSandpackFiles(files);
    const compileDone = options?.compileChecked !== undefined;
    set((state) => ({
      generatedFiles: sandpackFiles,
      generatedFileCount: Object.keys(sandpackFiles).length,
      recentFiles: Object.keys(sandpackFiles).slice(-5).reverse(),
      filesRevision: state.filesRevision + 1,
      isGenerating: false,
      isAssembling: false,
      generationStep: null,
      generationStepTitle: compileDone
        ? options?.compileChecked
          ? "生成完成"
          : "生成完成（编译有告警）"
        : "组装中...",
      // 每次全量 files 都 remount，确保最终 compile 结果进入预览
      previewReadyKey: state.previewReadyKey + 1,
    }));
  },
  mergeGeneratedFiles: (files, meta) =>
    set((state) => {
      const merged: SandpackFiles = { ...(state.generatedFiles ?? {}) };
      const newPaths: string[] = [];

      Object.entries(files as Record<string, RawFileValue>).forEach(([path, value]) => {
        merged[path] = { code: normalizeCode(value) };
        newPaths.push(path);
      });

      const recentFiles = [
        ...newPaths.reverse(),
        ...state.recentFiles.filter((path) => !newPaths.includes(path)),
      ].slice(0, 5);

      return {
        generatedFiles: merged,
        generatedFileCount: Object.keys(merged).length,
        recentFiles,
        generationStep: meta?.step ?? state.generationStep,
        generationStepTitle: meta?.stepTitle ?? state.generationStepTitle,
        filesRevision: state.filesRevision + 1,
      };
    }),
  clearGeneratedFiles: () =>
    set((state) => ({
      generatedFiles: null,
      generatedFileCount: 0,
      recentFiles: [],
      filesRevision: state.filesRevision + 1,
    })),

  isGenerating: false,
  generationSessionId: null,
  generationStep: null,
  generationStepTitle: "准备生成...",
  generatedFileCount: 0,
  recentFiles: [],
  filesRevision: 0,
  previewReadyKey: 0,
  startGeneration: (sessionId) =>
    set((state) => ({
      isGenerating: true,
      isAssembling: false,
      generationSessionId: sessionId,
      generationStep: null,
      generationStepTitle: "正在分析需求...",
      generatedFiles: {},
      generatedFileCount: 0,
      recentFiles: [],
      filesRevision: state.filesRevision + 1,
    })),
  updateGenerationStep: (step, stepTitle) =>
    set({
      generationStep: step,
      generationStepTitle: stepTitle,
    }),
  finishGeneration: () =>
    set({
      isGenerating: false,
      isAssembling: false,
      generationStep: null,
    }),
  /** 全量 files 就绪：结束组装遮罩并强制 Sandpack 重新挂载预览 */
  completeGeneration: () =>
    set((state) => ({
      isGenerating: false,
      isAssembling: false,
      generationStep: null,
      generationStepTitle: "生成完成",
      previewReadyKey: state.previewReadyKey + 1,
      filesRevision: state.filesRevision + 1,
    })),

  isAssembling: false,
  setIsAssembling: (isAssembling) => set({ isAssembling }),
}));
