"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, X } from "lucide-react";
import {
  loadFigmaOAuthConfig,
  type FigmaOAuthConfig,
} from "@/lib/figmaOAuthConfig";
import { fetchFigmaOAuthConfigInfo } from "@/services/figmaApi";

type FigmaOAuthDialogProps = {
  open: boolean;
  onClose: () => void;
  onSubmit: (config: FigmaOAuthConfig) => Promise<void>;
  loading?: boolean;
};

export function FigmaOAuthDialog({
  open,
  onClose,
  onSubmit,
  loading = false,
}: FigmaOAuthDialogProps) {
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [redirectUri, setRedirectUri] = useState(
    "http://localhost:7001/api/figma/oauth/callback",
  );
  const [docsUrl, setDocsUrl] = useState(
    "https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/",
  );

  useEffect(() => {
    if (!open) return;
    const saved = loadFigmaOAuthConfig();
    if (saved) {
      setClientId(saved.clientId);
      setClientSecret(saved.clientSecret);
    }
    void fetchFigmaOAuthConfigInfo().then((info) => {
      setRedirectUri(info.redirectUri);
      setDocsUrl(info.docsUrl);
    });
  }, [open]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!clientId.trim() || !clientSecret.trim()) return;
      await onSubmit({
        clientId: clientId.trim(),
        clientSecret: clientSecret.trim(),
      });
    },
    [clientId, clientSecret, onSubmit],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-labelledby="figma-oauth-title"
        className="w-full max-w-md rounded-xl border border-[var(--lab-border)] bg-white p-5 shadow-xl ring-1 ring-[#a259ff]/20"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-2">
          <div>
            <h2
              id="figma-oauth-title"
              className="text-base font-semibold text-gray-900"
            >
              连接 Figma MCP
            </h2>
            <p className="mt-1 text-xs text-gray-500">
              填写你在 Figma 开发者后台创建的 OAuth 应用凭证
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:bg-gray-100"
            aria-label="关闭"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">
              Client ID
            </label>
            <input
              type="text"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="OAuth 应用的 Client ID"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#a259ff] focus:ring-1 focus:ring-[#a259ff]/30"
              autoComplete="off"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">
              Client Secret
            </label>
            <input
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder="OAuth 应用的 Client Secret"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-[#a259ff] focus:ring-1 focus:ring-[#a259ff]/30"
              autoComplete="off"
            />
          </div>

          <div className="rounded-lg bg-gray-50 px-3 py-2">
            <p className="text-[10px] font-medium text-gray-600">回调地址（复制到 Figma OAuth 应用）</p>
            <p className="mt-1 break-all font-mono text-[10px] text-gray-800">
              {redirectUri}
            </p>
          </div>

          <a
            href={docsUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="flex items-center gap-1 text-[11px] text-[#7c3aed] hover:underline"
          >
            如何创建 Figma MCP OAuth 应用
            <ExternalLink size={12} />
          </a>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading || !clientId.trim() || !clientSecret.trim()}
              className="flex-1 rounded-lg bg-[#a259ff] px-3 py-2 text-sm font-medium text-white hover:bg-[#8b3fd9] disabled:opacity-50"
            >
              {loading ? "连接中..." : "保存并打开授权页"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
