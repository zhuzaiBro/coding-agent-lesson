import type { SandpackFiles } from "@/types/store";
import {
  getPreviewDependencies,
  getPreviewDevDependencies,
} from "./sandpackDependencies";

/** 生产 Nodebox 必须用 Vite 4 + esbuild-wasm，始终注入 customSetup（含仅模板预览时） */
export function getSandpackCustomSetup(files: SandpackFiles | null) {
  const hasIndexEntry = Boolean(files?.["/index.tsx"]?.code?.includes("createRoot"));

  return {
    entry: hasIndexEntry ? "/index.tsx" : "/App.tsx",
    environment: "node" as const,
    dependencies: getPreviewDependencies(files),
    devDependencies: getPreviewDevDependencies(files),
  };
}
