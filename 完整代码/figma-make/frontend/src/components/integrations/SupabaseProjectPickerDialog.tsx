"use client";

import { useCallback, useState } from "react";
import { Database, Loader2, X } from "lucide-react";
import type { SupabaseProjectItem } from "@/services/supabaseApi";
import { selectSupabaseProject } from "@/services/supabaseApi";

type SupabaseProjectPickerDialogProps = {
  open: boolean;
  projects: SupabaseProjectItem[];
  onComplete: () => Promise<void>;
  onClose?: () => void;
};

export function SupabaseProjectPickerDialog({
  open,
  projects,
  onComplete,
  onClose,
}: SupabaseProjectPickerDialogProps) {
  const [selectedRef, setSelectedRef] = useState(
    () => projects[0]?.ref ?? "",
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = useCallback(async () => {
    const project = projects.find((p) => p.ref === selectedRef);
    if (!project) return;

    setSubmitting(true);
    setError(null);
    try {
      await selectSupabaseProject(project);
      await onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存项目选择失败");
    } finally {
      setSubmitting(false);
    }
  }, [projects, selectedRef, onComplete]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-labelledby="supabase-project-picker-title"
        className="flex max-h-[85vh] w-full max-w-md flex-col rounded-xl border border-[var(--lab-border)] bg-white shadow-xl ring-1 ring-[#3ecf8e]/20"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-2 border-b border-gray-100 p-5 pb-4">
          <div>
            <h2
              id="supabase-project-picker-title"
              className="flex items-center gap-2 text-base font-semibold text-gray-900"
            >
              <Database size={18} className="text-[#1a7f4b]" />
              选择 Supabase 项目
            </h2>
            <p className="mt-1 text-xs text-gray-500">
              授权已完成，请选择要连接的数据库项目（将保存在当前会话，无需改服务器
              .env）
            </p>
          </div>
          {onClose ? (
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              aria-label="关闭"
            >
              <X size={18} />
            </button>
          ) : null}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-5 pt-3">
          <ul className="space-y-2">
            {projects.map((project) => {
              const active = project.ref === selectedRef;
              return (
                <li key={project.ref}>
                  <button
                    type="button"
                    disabled={submitting}
                    onClick={() => setSelectedRef(project.ref)}
                    className={`w-full rounded-lg border px-3 py-2.5 text-left transition-colors disabled:opacity-60 ${
                      active
                        ? "border-[#3ecf8e] bg-[#3ecf8e]/10 ring-1 ring-[#3ecf8e]/40"
                        : "border-gray-200 hover:border-[#3ecf8e]/50 hover:bg-[#f4ffe8]"
                    }`}
                  >
                    <div className="text-sm font-medium text-gray-900">
                      {project.name}
                    </div>
                    <div className="mt-0.5 font-mono text-xs text-gray-500">
                      {project.ref}
                      {project.region ? ` · ${project.region}` : ""}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
          {error ? (
            <p className="mt-3 text-xs text-red-600">{error}</p>
          ) : null}
        </div>

        <div className="border-t border-gray-100 p-5 pt-4">
          <button
            type="button"
            disabled={submitting || !selectedRef}
            onClick={() => void handleConfirm()}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#3ecf8e] px-4 py-2.5 text-sm font-medium text-white transition-opacity hover:bg-[#2eb87a] disabled:opacity-60"
          >
            {submitting ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                正在连接...
              </>
            ) : (
              "确认并连接"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
