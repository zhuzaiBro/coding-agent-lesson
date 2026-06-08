"use client";

import { LabLoading } from "@/components/ui/LabLoading";

export function BuildingLoadingOverlay() {
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-[#f4ffe8] via-white to-[#fff5eb]">
      <div className="flex flex-col items-center gap-6">
        <LabLoading size="lg" message="正在组装你的应用..." />
        <div className="flex items-center gap-2 rounded-full border border-[var(--lab-green)]/30 bg-white/80 px-4 py-2 shadow-sm backdrop-blur-sm">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--lab-green)] opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--lab-green)]" />
          </span>
          <span className="text-sm text-[var(--lab-text-muted)]">
            化学反应进行中
          </span>
        </div>
      </div>
    </div>
  );
}
