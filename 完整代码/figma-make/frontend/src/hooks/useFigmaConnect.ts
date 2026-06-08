"use client";

import { useCallback, useState } from "react";
import {
  openFigmaAuthorizePage,
  logoutFigmaOAuth,
  persistFigmaOAuthConfig,
  clearFigmaOAuthConfigLocal,
} from "@/lib/figmaAuth";
import { loadFigmaOAuthConfig, type FigmaOAuthConfig } from "@/lib/figmaOAuthConfig";
import { useFigmaStore } from "@/store/figmaStore";

export function useFigmaConnect(
  onToast?: (message: string, type?: "info" | "warning" | "error") => void,
) {
  const linked = useFigmaStore((s) => s.linked);
  const connectionState = useFigmaStore((s) => s.connectionState);
  const checkConnection = useFigmaStore((s) => s.checkConnection);
  const disconnectStore = useFigmaStore((s) => s.disconnect);

  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [configSubmitting, setConfigSubmitting] = useState(false);

  const isConnecting = connectionState === "loading" || configSubmitting;

  const connectWithOAuth = useCallback(async () => {
    try {
      const opened = await openFigmaAuthorizePage();
      if (!opened.ok) {
        onToast?.(opened.message, "error");
        return;
      }
      onToast?.(opened.message, "info");
    } catch (error) {
      onToast?.(
        error instanceof Error ? error.message : "打开 Figma 授权失败",
        "error",
      );
    }
  }, [onToast]);

  const submitOAuthConfig = useCallback(
    async (config: FigmaOAuthConfig) => {
      setConfigSubmitting(true);
      try {
        await persistFigmaOAuthConfig(config);
        setConfigDialogOpen(false);
        await connectWithOAuth();
      } catch (error) {
        onToast?.(
          error instanceof Error ? error.message : "保存 OAuth 配置失败",
          "error",
        );
      } finally {
        setConfigSubmitting(false);
      }
    },
    [connectWithOAuth, onToast],
  );

  const finishAfterAuth = useCallback(async () => {
    const status = await checkConnection();
    if (status.ok) {
      onToast?.("Figma MCP 已连接", "info");
    } else {
      onToast?.(status.message ?? "Figma 连接失败", "error");
    }
    return status;
  }, [checkConnection, onToast]);

  const disconnect = useCallback(async () => {
    await logoutFigmaOAuth().catch(() => undefined);
    clearFigmaOAuthConfigLocal();
    disconnectStore();
    onToast?.("已断开 Figma", "info");
  }, [disconnectStore, onToast]);

  const handleConnectClick = useCallback(async () => {
    if (isConnecting) return;
    if (linked) {
      await disconnect();
      return;
    }

    const saved = loadFigmaOAuthConfig();
    if (saved?.clientId && saved?.clientSecret) {
      await connectWithOAuth();
      return;
    }

    setConfigDialogOpen(true);
  }, [isConnecting, linked, disconnect, connectWithOAuth]);

  return {
    linked,
    connectionState,
    isConnecting,
    configDialogOpen,
    setConfigDialogOpen,
    configSubmitting,
    submitOAuthConfig,
    finishAfterAuth,
    disconnect,
    handleConnectClick,
    checkConnection,
  };
}
