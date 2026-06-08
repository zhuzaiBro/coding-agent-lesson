"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Figma, Loader2 } from "lucide-react";
import { useFigmaConnect } from "@/hooks/useFigmaConnect";

function FigmaAuthCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { finishAfterAuth } = useFigmaConnect();
  const [message, setMessage] = useState("正在完成 Figma 授权...");

  useEffect(() => {
    const error = searchParams.get("error");
    if (error) {
      setMessage(`授权失败：${error}`);
      return;
    }
    if (!searchParams.get("success")) {
      setMessage("缺少授权结果");
      return;
    }
    void finishAfterAuth().then((status) => {
      if (status.ok) {
        setMessage("授权成功，正在返回...");
        router.replace("/");
      } else {
        setMessage(status.message ?? "连接失败");
      }
    });
  }, [searchParams, finishAfterAuth, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#faf5ff] p-6">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#a259ff]/15 text-[#7c3aed]">
        <Figma size={28} />
      </div>
      <p className="flex items-center gap-2 text-sm text-gray-700">
        <Loader2 size={16} className="animate-spin" />
        {message}
      </p>
    </div>
  );
}

export default function FigmaAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-gray-600">
          <Loader2 className="mr-2 animate-spin" size={16} />
          正在处理 Figma 授权...
        </div>
      }
    >
      <FigmaAuthCallbackContent />
    </Suspense>
  );
}
