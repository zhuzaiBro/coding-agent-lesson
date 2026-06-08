import {
  loadFigmaOAuthConfig,
  saveFigmaOAuthConfigLocal,
  type FigmaOAuthConfig,
} from "@/lib/figmaOAuthConfig";
import { saveFigmaOAuthConfig, startFigmaOAuth } from "@/services/figmaApi";

export async function persistFigmaOAuthConfig(
  config: FigmaOAuthConfig,
): Promise<void> {
  saveFigmaOAuthConfigLocal(config);
  await saveFigmaOAuthConfig(config);
}

/** 打开 Figma 官方 MCP OAuth 授权页（需已保存 Client ID / Secret） */
export async function openFigmaAuthorizePage(): Promise<{
  ok: boolean;
  authorizeUrl?: string;
  message: string;
}> {
  const saved = loadFigmaOAuthConfig();
  if (saved) {
    await persistFigmaOAuthConfig(saved);
  }

  const res = await startFigmaOAuth();
  if (!res.authorizeUrl) {
    return { ok: false, message: "服务端未返回 Figma 授权地址" };
  }

  window.open(res.authorizeUrl, "_blank", "noopener,noreferrer");
  return {
    ok: true,
    authorizeUrl: res.authorizeUrl,
    message: "已在浏览器打开 Figma MCP 授权页，完成后将自动返回应用",
  };
}

export { clearFigmaOAuthConfigLocal } from "@/lib/figmaOAuthConfig";
export { logoutFigmaOAuth } from "@/services/figmaApi";
