import { API_BASE_URL } from "@/constants/config";

export type SupabaseStatusResponse = {
  configured: boolean;
  ok?: boolean;
  projectUrl?: string;
  mcpUrl?: string;
  message?: string;
};

export type SupabaseClientConfigResponse = {
  projectUrl: string;
  publishableKeys: string;
  envExample: {
    VITE_SUPABASE_URL: string;
    VITE_SUPABASE_ANON_KEY: string;
  };
};

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchSupabaseStatus(): Promise<SupabaseStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/supabase/status`, {
    cache: "no-store",
    credentials: "include",
  });
  return parseJson<SupabaseStatusResponse>(res);
}

export async function fetchSupabaseClientConfig(): Promise<SupabaseClientConfigResponse> {
  const res = await fetch(`${API_BASE_URL}/api/supabase/client-config`, {
    cache: "no-store",
    credentials: "include",
  });
  return parseJson<SupabaseClientConfigResponse>(res);
}
