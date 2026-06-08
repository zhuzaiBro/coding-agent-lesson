"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Database, Loader2 } from "lucide-react";
import { useSupabaseConnect } from "@/hooks/useSupabaseConnect";

function SupabaseAuthCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { finishAfterAuth } = useSupabaseConnect();
  const [message, setMessage] = useState("正在完成 Supabase 授权...");

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

    void finishAfterAuth().then((result) => {
      if (result.ok) {
        setMessage("授权成功，正在返回应用...");
        router.replace("/");
      } else {
        setMessage(result.message);
      }
    });
  }, [searchParams, finishAfterAuth, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#fafff5] p-6">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#3ecf8e]/15 text-[#1a7f4b]">
        <Database size={28} />
      </div>
      <p className="flex items-center gap-2 text-sm text-gray-700">
        <Loader2 size={16} className="animate-spin" />
        {message}
      </p>
    </div>
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
