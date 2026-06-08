"use client";

import { useCallback } from "react";
import {
  openSupabaseAuthorizePage,
  logoutSupabaseOAuth,
} from "@/lib/supabaseAuth";
import {
  useSupabaseStore,
  type ConnectToAppResult,
} from "@/store/supabaseStore";

export function useSupabaseConnect(
  onToast?: (message: string, type?: "info" | "warning" | "error") => void,
) {
  const enabled = useSupabaseStore((s) => s.enabled);
  const linked = useSupabaseStore((s) => s.linked);
  const connectionState = useSupabaseStore((s) => s.connectionState);
  const connectToApp = useSupabaseStore((s) => s.connectToApp);
  const disconnectFromApp = useSupabaseStore((s) => s.disconnectFromApp);

  const isConnecting = connectionState === "loading";

  /** 打开浏览器 Supabase 授权页 */
  const connect = useCallback(async (): Promise<ConnectToAppResult> => {
    const opened = await openSupabaseAuthorizePage();
    if (!opened.ok) {
      onToast?.(opened.message, "error");
      return { ok: false, configured: false, message: opened.message };
    }
    onToast?.(opened.message, "info");
    return { ok: true, configured: true, message: opened.message };
  }, [onToast]);

  /** 授权回调后：拉 MCP 配置并写入应用 */
  const finishAfterAuth = useCallback(async () => {
    const result = await connectToApp();
    if (result.ok) {
      onToast?.("Supabase 已连接到你的应用", "info");
    } else {
      onToast?.(result.message, "error");
    }
    return result;
  }, [connectToApp, onToast]);

  const disconnect = useCallback(async () => {
    await logoutSupabaseOAuth();
    disconnectFromApp();
    onToast?.("已断开 Supabase", "info");
  }, [disconnectFromApp, onToast]);

  const handleConnectClick =
    useCallback(async (): Promise<ConnectToAppResult | undefined> => {
      if (isConnecting) return undefined;
      if (enabled && linked) {
        await disconnect();
        return undefined;
      }
      return connect();
    }, [isConnecting, enabled, linked, disconnect, connect]);

  return {
    enabled,
    linked,
    connectionState,
    isConnecting,
    connect,
    finishAfterAuth,
    disconnect,
    handleConnectClick,
  };
}
