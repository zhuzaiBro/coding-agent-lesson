"use client";

import { useSandpack } from "@codesandbox/sandpack-react";
import { useEffect, useState } from "react";

/**
 * 预览 bundler 报错时展示（避免纯白屏看不出原因）。
 */
export function SandpackErrorOverlay() {
  const { sandpack, listen } = useSandpack();
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (sandpack.error) {
      setMessage(
        typeof sandpack.error === "string"
          ? sandpack.error
          : (sandpack.error as Error)?.message ?? "预览编译失败",
      );
    }
  }, [sandpack.error]);

  useEffect(() => {
    const unsubscribe = listen((msg) => {
      if (msg.type === "action" && msg.action === "show-error") {
        const payload = msg as { message?: string; title?: string };
        const text = [payload.title, payload.message].filter(Boolean).join("\n");
        if (text) setMessage(text);
      }
    });
    return unsubscribe;
  }, [listen]);

  if (!message) return null;

  return (
    <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center bg-white/90 p-6">
      <div className="pointer-events-auto max-h-[70%] max-w-lg overflow-auto rounded-xl border border-red-200 bg-red-50 p-4 shadow-lg">
        <h3 className="text-sm font-semibold text-red-800">预览运行失败</h3>
        <pre className="mt-2 whitespace-pre-wrap break-words font-mono text-xs text-red-900">
          {message}
        </pre>
        <p className="mt-3 text-xs text-red-700/80">
          服务端编译可能已通过，但 Sandpack 环境与 Vite 不完全一致。可在代码视图查看具体文件。
        </p>
      </div>
    </div>
  );
}
