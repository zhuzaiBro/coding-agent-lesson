import { API_BASE_URL } from "@/constants/config";

export type SupabaseStatusResponse = {
  configured: boolean;
  ok?: boolean;
  projectUrl?: string;
  projectRef?: string | null;
  mcpUrl?: string;
  message?: string;
  schemaReady?: boolean;
  needsProjectRef?: boolean;
  needsProjectSelection?: boolean;
};

export type SupabaseProjectItem = {
  ref: string;
  name: string;
  region?: string;
  source?: string;
};

export type SupabaseSelectedProjectResponse = {
  selected: SupabaseProjectItem | null;
  needsSelection: boolean;
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

export async function fetchSupabaseProjects(): Promise<SupabaseProjectItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/supabase/oauth/projects`, {
    cache: "no-store",
    credentials: "include",
  });
  const data = await parseJson<{ projects: SupabaseProjectItem[] }>(res);
  return data.projects ?? [];
}

export async function fetchSupabaseSelectedProject(): Promise<SupabaseSelectedProjectResponse> {
  const res = await fetch(`${API_BASE_URL}/api/supabase/oauth/project`, {
    cache: "no-store",
    credentials: "include",
  });
  return parseJson<SupabaseSelectedProjectResponse>(res);
}

export async function selectSupabaseProject(
  project: Pick<SupabaseProjectItem, "ref" | "name">,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/supabase/oauth/project`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      projectRef: project.ref,
      projectName: project.name,
    }),
  });
  await parseJson<{ ok: boolean }>(res);
}
