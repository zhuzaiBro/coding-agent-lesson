"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Database, Loader2 } from "lucide-react";
import { useSupabaseConnect } from "@/hooks/useSupabaseConnect";
import { API_BASE_URL } from "@/constants/config";
import { SupabaseProjectPickerDialog } from "@/components/integrations/SupabaseProjectPickerDialog";
import {
  fetchSupabaseProjects,
  fetchSupabaseSelectedProject,
  selectSupabaseProject,
  type SupabaseProjectItem,
} from "@/services/supabaseApi";

const PROD_FRONTEND_ORIGIN = "https://coding.zood.work";

/**
 * 本地 dev（localhost:3000）连线上 API 时，OAuth 应在线上前端完成回调；
 * 若仍落在 localhost，自动跳到线上同路径（Cookie 在 API 域，localhost 无法带 Cookie）。
 */
function useRedirectLocalhostToProdIfNeeded(search: string) {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const { hostname, pathname, search: q } = window.location;
    if (hostname !== "localhost" && hostname !== "127.0.0.1") return;
    const apiIsProd = !API_BASE_URL.includes("localhost");
    if (!apiIsProd) return;
    const target = `${PROD_FRONTEND_ORIGIN}${pathname}${q || search}`;
    window.location.replace(target);
  }, [search]);
}

function SupabaseAuthCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { finishAfterAuth } = useSupabaseConnect();
  const [message, setMessage] = useState("正在完成 Supabase 授权...");
  const [showPicker, setShowPicker] = useState(false);
  const [projects, setProjects] = useState<SupabaseProjectItem[]>([]);
  const queryString = searchParams.toString();
  const search = queryString ? `?${queryString}` : "";

  useRedirectLocalhostToProdIfNeeded(search);

  const completeConnection = useCallback(async () => {
    setMessage("正在配置应用...");
    const result = await finishAfterAuth();
    if (result.ok) {
      setMessage("授权成功，正在返回应用...");
      router.replace("/");
    } else {
      setMessage(result.message);
    }
    return result;
  }, [finishAfterAuth, router]);

  useEffect(() => {
    const error = searchParams.get("error");
    if (error) {
      setMessage(`授权失败：${error}`);
      return;
    }

    const success = searchParams.get("success");
    if (!success) {
      setMessage("缺少授权结果，请返回应用重新点击 Supabase");
      return;
    }

    void (async () => {
      setMessage("授权成功，正在检查项目绑定...");

      try {
        const selection = await fetchSupabaseSelectedProject();
        if (selection.selected?.ref) {
          await completeConnection();
          return;
        }

        if (!selection.needsSelection) {
          setMessage("授权未完成，请返回应用重新点击 Supabase");
          return;
        }

        setMessage("正在加载可访问的 Supabase 项目...");
        const list = await fetchSupabaseProjects();

        if (list.length === 1) {
          setMessage(`已自动选择项目 ${list[0].name}...`);
          await selectSupabaseProject(list[0]);
          await completeConnection();
          return;
        }

        setProjects(list);
        setShowPicker(true);
        setMessage("请选择要连接的 Supabase 项目");
      } catch (err) {
        setMessage(
          err instanceof Error ? err.message : "加载项目列表失败",
        );
      }
    })();
  }, [searchParams, completeConnection]);

  return (
    <>
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#fafff5] p-6">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#3ecf8e]/15 text-[#1a7f4b]">
          <Database size={28} />
        </div>
        <p className="flex items-center gap-2 text-sm text-gray-700">
          {!showPicker ? (
            <Loader2 size={16} className="animate-spin" />
          ) : null}
          {message}
        </p>
      </div>

      <SupabaseProjectPickerDialog
        open={showPicker}
        projects={projects}
        onComplete={completeConnection}
      />
    </>
  );
}

export default function SupabaseAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-gray-600">
          <Loader2 className="mr-2 animate-spin" size={16} />
          正在处理授权...
        </div>
      }
    >
      <SupabaseAuthCallbackContent />
    </Suspense>
  );
}
