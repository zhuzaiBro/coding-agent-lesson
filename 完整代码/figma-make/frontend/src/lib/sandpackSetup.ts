import type { SandpackFiles } from "@/types/store";
import {
  getPreviewDependencies,
  getPreviewDevDependencies,
} from "./sandpackDependencies";

export function getSandpackCustomSetup(files: SandpackFiles | null) {
  const hasGenerated =
    files !== null && Object.keys(files).length > 0 && Boolean(files["/App.tsx"]);

  if (!hasGenerated) {
    return undefined;
  }

  return {
    entry: files["/index.tsx"] ? "/index.tsx" : "/App.tsx",
    /** 与本地 compile-check 一致，使用 Vite 而非 CRA（避免 react-scripts 缺失导致 iframe 白屏） */
    environment: "node" as const,
    dependencies: getPreviewDependencies(files),
    devDependencies: getPreviewDevDependencies(files),
  };
}
