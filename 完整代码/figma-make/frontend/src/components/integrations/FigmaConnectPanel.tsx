"use client";

import { Figma } from "lucide-react";
import { useFigmaConnect } from "@/hooks/useFigmaConnect";
import { FigmaOAuthDialog } from "@/components/integrations/FigmaOAuthDialog";

function FigmaConnectControl({
  onToast,
  variant,
}: {
  onToast?: (message: string, type?: "info" | "warning" | "error") => void;
  variant: "chat" | "header";
}) {
  const {
    linked,
    connectionState,
    isConnecting,
    configDialogOpen,
    setConfigDialogOpen,
    configSubmitting,
    submitOAuthConfig,
    handleConnectClick,
  } = useFigmaConnect(onToast);

  const statusDot =
    linked
      ? "bg-[#a259ff]"
      : isConnecting
        ? "bg-amber-400 animate-pulse"
        : connectionState === "error"
          ? "bg-red-500"
          : "bg-gray-300";

  const button =
    variant === "chat" ? (
      <button
        type="button"
        title={
          linked
            ? "Figma MCP 已连接（点击断开）"
            : "连接 Figma MCP（填写 OAuth 后打开授权页）"
        }
        disabled={isConnecting}
        onClick={() => void handleConnectClick()}
        className={`relative flex items-center gap-1 rounded-md px-2 py-1 text-sm transition-colors disabled:opacity-60 ${
          linked
            ? "bg-[#a259ff]/15 text-[#7c3aed] ring-1 ring-[#a259ff]/40"
            : "text-gray-500 hover:bg-gray-100 hover:text-gray-800"
        }`}
      >
        <Figma size={18} className={isConnecting ? "animate-pulse" : undefined} />
        <span className="hidden sm:inline text-xs font-medium">
          {linked ? "Figma 已连" : "Figma"}
        </span>
        <span
          className={`absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full ${statusDot}`}
        />
      </button>
    ) : (
      <button
        type="button"
        disabled={isConnecting}
        title={linked ? "Figma MCP 已连接" : "连接 Figma MCP"}
        onClick={() => void handleConnectClick()}
        className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-all disabled:opacity-60 ${
          linked
            ? "border-[#a259ff]/50 bg-[#a259ff]/10 text-[#7c3aed]"
            : "border-[var(--lab-border)] bg-white text-gray-600 hover:bg-[#faf5ff]"
        }`}
      >
        <Figma size={16} className={isConnecting ? "animate-pulse" : undefined} />
        {linked ? "Figma 已连" : "Figma"}
      </button>
    );

  return (
    <>
      {button}
      <FigmaOAuthDialog
        open={configDialogOpen}
        onClose={() => setConfigDialogOpen(false)}
        onSubmit={submitOAuthConfig}
        loading={configSubmitting}
      />
    </>
  );
}

export function FigmaConnectButton({
  onToast,
}: {
  onToast?: (message: string, type?: "info" | "warning" | "error") => void;
}) {
  return <FigmaConnectControl onToast={onToast} variant="chat" />;
}

export function FigmaHeaderConnectButton({
  onToast,
}: {
  onToast?: (message: string, type?: "info" | "warning" | "error") => void;
}) {
  return <FigmaConnectControl onToast={onToast} variant="header" />;
}
