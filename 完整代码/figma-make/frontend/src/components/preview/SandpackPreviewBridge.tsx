"use client";

import { useSandpack, useSandpackNavigation } from "@codesandbox/sandpack-react";
import { useEffect, useRef } from "react";

const VITE_READY_RE =
  /ready in|Local:\s*http|➜\s*Local|localhost:\d+/i;

/**
 * Vite + node 环境：dev server 日志会占满 LoadingOverlay。
 * 在 server ready 或 compile done 后多次 refresh，把 preview URL 载入 iframe。
 */
export function SandpackPreviewBridge() {
  const { listen, sandpack } = useSandpack();
  const { refresh } = useSandpackNavigation();
  const scheduledRef = useRef(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const statusRef = useRef(sandpack.status);
  statusRef.current = sandpack.status;

  const scheduleRefresh = () => {
    if (scheduledRef.current) return;
    scheduledRef.current = true;

    const delays = [0, 400, 1200, 2500];
    for (const ms of delays) {
      const id = setTimeout(() => {
        if (statusRef.current !== "running") return;
        refresh();
      }, ms);
      timersRef.current.push(id);
    }

    const resetId = setTimeout(() => {
      scheduledRef.current = false;
    }, 4000);
    timersRef.current.push(resetId);
  };

  useEffect(() => {
    scheduledRef.current = false;
    return () => {
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
    };
  }, [listen, sandpack.environment]);

  useEffect(() => {
    const unsubscribe = listen((message) => {
      if (message.type === "done" && !("compilatonError" in message && message.compilatonError)) {
        scheduleRefresh();
        return;
      }

      if (message.type === "urlchange" && "url" in message && typeof message.url === "string") {
        const iframe = document.querySelector<HTMLIFrameElement>(
          ".sandpack-wrapper .sp-preview-iframe",
        );
        if (iframe && iframe.src !== message.url) {
          iframe.src = message.url;
        }
        return;
      }

      if (message.type === "stdout") {
        const payload = message as { payload?: { data?: string } };
        const text = payload.payload?.data ?? "";
        if (VITE_READY_RE.test(text)) {
          scheduleRefresh();
        }
      }
    });

    return unsubscribe;
  }, [listen, refresh, sandpack.status]);

  return null;
}
