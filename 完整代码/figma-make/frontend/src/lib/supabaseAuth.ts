import { API_BASE_URL } from "@/constants/config";

/** 打开 Supabase 官方 OAuth 授权页（新标签页） */
export async function openSupabaseAuthorizePage(): Promise<{
  ok: boolean;
  authorizeUrl?: string;
  message: string;
}> {
  const res = await fetch(`${API_BASE_URL}/api/supabase/oauth/start`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text();
    return {
      ok: false,
      message: text || `无法启动授权 (${res.status})`,
    };
  }

  const data = (await res.json()) as { authorizeUrl?: string };
  if (!data.authorizeUrl) {
    return { ok: false, message: "服务端未返回授权地址" };
  }

  window.open(data.authorizeUrl, "_blank", "noopener,noreferrer");
  return {
    ok: true,
    authorizeUrl: data.authorizeUrl,
    message: "已在浏览器打开 Supabase 授权页，完成后将自动返回应用",
  };
}

export async function logoutSupabaseOAuth(): Promise<void> {
  await fetch(`${API_BASE_URL}/api/supabase/oauth/logout`, {
    method: "POST",
    credentials: "include",
  });
}
