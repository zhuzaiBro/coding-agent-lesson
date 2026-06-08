"use client";

import { useEffect, useState } from "react";
import { useChatStore } from "@/store/chatStore";
import { restoreSandpackFromVersions } from "@/lib/workspacePersistence";
import { LabLoading } from "@/components/ui/LabLoading";

/**
 * 从 localStorage 恢复聊天 / 版本记录，并加载最近一次生成的代码到 Sandpack。
 */
export function WorkspaceHydrator({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;

      const { versions, messages } = useChatStore.getState();
      if (versions.length > 0) {
        restoreSandpackFromVersions(versions);
        console.log("[Workspace] Restored from localStorage:", {
          messages: messages.length,
          versions: versions.length,
        });
      }
      setReady(true);
    };

    const unsub = useChatStore.persist.onFinishHydration(finish);
    void Promise.resolve(useChatStore.persist.rehydrate()).then(() => {
      if (useChatStore.persist.hasHydrated()) {
        finish();
      }
    });

    return unsub;
  }, []);

  if (!ready) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[var(--background)]">
        <LabLoading size="md" message="正在恢复工作区..." />
      </div>
    );
  }

  return <>{children}</>;
}
