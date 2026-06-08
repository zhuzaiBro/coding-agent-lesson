const STORAGE_KEY = "zood-figma-oauth-config";

export type FigmaOAuthConfig = {
  clientId: string;
  clientSecret: string;
};

export function loadFigmaOAuthConfig(): FigmaOAuthConfig | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as FigmaOAuthConfig;
    if (parsed.clientId && parsed.clientSecret) return parsed;
  } catch {
    // ignore
  }
  return null;
}

export function saveFigmaOAuthConfigLocal(config: FigmaOAuthConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

export function clearFigmaOAuthConfigLocal() {
  localStorage.removeItem(STORAGE_KEY);
}
