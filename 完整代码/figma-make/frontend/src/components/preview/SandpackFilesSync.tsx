"use client";

import { useSandpack } from "@codesandbox/sandpack-react";
import { useCallback, useEffect, useRef } from "react";
import {
  getSandpackActiveFile,
  listSandpackSyncEntries,
  mergeSandpackFiles,
} from "@/lib/mergeSandpackFiles";
import { useSandpackStore } from "@/store/sandpackStore";

interface SandpackFilesSyncProps {
  templateFiles: Record<string, { code: string }>;
}

const RUN_SANDPACK_DEBOUNCE_MS = 280;

/**
 * SandpackProvider 挂载后不会自动响应 files prop 增量变化，
 * 需要在内部用 updateFile 同步新文件到文件树。
 */
export function SandpackFilesSync({ templateFiles }: SandpackFilesSyncProps) {
  const { sandpack } = useSandpack();
  const filesRevision = useSandpackStore((s) => s.filesRevision);
  const generationSessionId = useSandpackStore((s) => s.generationSessionId);
  const previewReadyKey = useSandpackStore((s) => s.previewReadyKey);

  const sandpackRef = useRef(sandpack);
  const syncedRef = useRef<Record<string, string>>({});
  const runTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    sandpackRef.current = sandpack;
  }, [sandpack]);

  const scheduleRunSandpack = useCallback(() => {
    if (runTimerRef.current) {
      clearTimeout(runTimerRef.current);
    }
    runTimerRef.current = setTimeout(() => {
      runTimerRef.current = null;
      sandpackRef.current.runSandpack();
    }, RUN_SANDPACK_DEBOUNCE_MS);
  }, []);

  const syncAllFiles = useCallback(
    (forceRun: boolean) => {
      const { generatedFiles, isGenerating, recentFiles } =
        useSandpackStore.getState();

      const mergedRecords = mergeSandpackFiles(templateFiles, generatedFiles);
      const hasApp =
        generatedFiles !== null && Object.keys(generatedFiles).length > 0;
      const entries = listSandpackSyncEntries(mergedRecords);

      let hasChanges = false;

      for (const [path, code] of entries) {
        if (!forceRun && syncedRef.current[path] === code) continue;
        sandpackRef.current.updateFile(path, code);
        syncedRef.current[path] = code;
        hasChanges = true;
      }

      if (hasApp) {
        for (const legacyPath of ["/vite.config.ts"]) {
          try {
            if (legacyPath in sandpackRef.current.files) {
              sandpackRef.current.deleteFile(legacyPath, false);
              delete syncedRef.current[legacyPath];
            }
          } catch {
            /* ignore */
          }
        }
      }

      if (!hasChanges && !forceRun) return;

      if (hasApp) {
        const activeFile = getSandpackActiveFile(generatedFiles);
        try {
          sandpackRef.current.openFile(activeFile);
        } catch (error) {
          console.warn(
            "[SandpackFilesSync] openFile failed:",
            activeFile,
            error,
          );
        }
      } else if (isGenerating && recentFiles[0]) {
        try {
          sandpackRef.current.openFile(recentFiles[0]);
        } catch (error) {
          console.warn(
            "[SandpackFilesSync] openFile failed:",
            recentFiles[0],
            error,
          );
        }
      }

      scheduleRunSandpack();
    },
    [templateFiles, scheduleRunSandpack],
  );

  useEffect(() => {
    syncedRef.current = {};
    return () => {
      if (runTimerRef.current) {
        clearTimeout(runTimerRef.current);
        runTimerRef.current = null;
      }
    };
  }, [generationSessionId, previewReadyKey]);

  useEffect(() => {
    syncAllFiles(false);
  }, [filesRevision, generationSessionId, templateFiles, syncAllFiles]);

  useEffect(() => {
    if (previewReadyKey <= 0) return;
    syncAllFiles(true);
    const retry = setTimeout(() => {
      sandpackRef.current.runSandpack();
    }, 500);
    return () => clearTimeout(retry);
  }, [previewReadyKey, syncAllFiles]);

  return null;
}
