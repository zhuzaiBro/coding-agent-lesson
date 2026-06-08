/** 从 MCP get_publishable_keys 文本中解析 anon key */
export function parseAnonKeyFromPublishableKeys(raw: string): string | null {
  const text = raw.trim();
  if (!text) return null;

  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    for (const key of ["anon", "anon_key", "anonKey", "VITE_SUPABASE_ANON_KEY"]) {
      const value = parsed[key];
      if (typeof value === "string" && value.startsWith("eyJ")) return value;
    }
  } catch {
    // not JSON
  }

  const labeled = text.match(
    /(?:anon|anonymous)[^\n]{0,40}?[`'"]?(eyJ[\w-]+\.[\w-]+\.[\w-]+)/i,
  );
  if (labeled?.[1]) return labeled[1];

  const jwts = text.match(/eyJ[\w-]+\.[\w-]+\.[\w-]+/g);
  return jwts?.[0] ?? null;
}

export function buildSupabaseEnvFile(
  projectUrl: string,
  anonKey: string | null,
): string {
  const lines = [`VITE_SUPABASE_URL=${projectUrl.trim()}`];
  if (anonKey) {
    lines.push(`VITE_SUPABASE_ANON_KEY=${anonKey}`);
  } else {
    lines.push("# VITE_SUPABASE_ANON_KEY=<set from Supabase dashboard>");
  }
  return `${lines.join("\n")}\n`;
}

