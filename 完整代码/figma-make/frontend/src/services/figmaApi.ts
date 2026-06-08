import { API_BASE_URL } from "@/constants/config";
import type { FigmaOAuthConfig } from "@/lib/figmaOAuthConfig";

export type FigmaStatusResponse = {
  ok?: boolean;
  mode?: "desktop" | "remote";
  mcpUrl?: string;
  configured?: boolean;
  message?: string;
  docsUrl?: string;
  tools?: string[];
};

export type FigmaOAuthConfigInfo = {
  redirectUri: string;
  docsUrl: string;
  hasStoredConfig?: boolean;
};

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchFigmaStatus(): Promise<FigmaStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/figma/status`, {
    cache: "no-store",
    credentials: "include",
  });
  return parseJson<FigmaStatusResponse>(res);
}

export async function fetchFigmaOAuthConfigInfo(): Promise<FigmaOAuthConfigInfo> {
  const res = await fetch(`${API_BASE_URL}/api/figma/oauth/config`, {
    cache: "no-store",
    credentials: "include",
  });
  return parseJson<FigmaOAuthConfigInfo>(res);
}

export async function saveFigmaOAuthConfig(
  config: FigmaOAuthConfig,
): Promise<FigmaOAuthConfigInfo> {
  const res = await fetch(`${API_BASE_URL}/api/figma/oauth/config`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_id: config.clientId,
      client_secret: config.clientSecret,
    }),
  });
  return parseJson(res);
}

export async function startFigmaOAuth(): Promise<{
  authorizeUrl: string;
  mode?: string;
  mcpUrl?: string;
}> {
  const res = await fetch(`${API_BASE_URL}/api/figma/oauth/start`, {
    cache: "no-store",
    credentials: "include",
  });
  return parseJson(res);
}

export async function logoutFigmaOAuth(): Promise<void> {
  await fetch(`${API_BASE_URL}/api/figma/oauth/logout`, {
    method: "POST",
    credentials: "include",
  });
}
