import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { fetchFigmaStatus, type FigmaStatusResponse } from "@/services/figmaApi";

export type FigmaConnectionState =
  | "idle"
  | "loading"
  | "connected"
  | "error";

export interface FigmaStore {
  linked: boolean;
  mode: "desktop" | "remote" | null;
  connectionState: FigmaConnectionState;
  mcpUrl: string | null;
  statusMessage: string | null;
  tools: string[];
  setLinked: (linked: boolean) => void;
  checkConnection: () => Promise<FigmaStatusResponse>;
  applyStatus: (status: FigmaStatusResponse) => void;
  disconnect: () => void;
}

export const useFigmaStore = create<FigmaStore>()(
  persist(
    (set, get) => ({
      linked: false,
      mode: null,
      connectionState: "idle",
      mcpUrl: null,
      statusMessage: null,
      tools: [],

      setLinked: (linked) => set({ linked }),

      applyStatus: (status) => {
        const ok = Boolean(status.ok);
        set({
          connectionState: ok ? "connected" : "error",
          linked: ok,
          mode: status.mode ?? get().mode,
          mcpUrl: status.mcpUrl ?? null,
          statusMessage:
            status.message ??
            (ok
              ? `Figma MCP 已连接（${status.mode ?? "desktop"}）`
              : "未连接 Figma MCP"),
          tools: status.tools ?? [],
        });
      },

      checkConnection: async () => {
        set({ connectionState: "loading", statusMessage: "正在检测 Figma MCP..." });
        try {
          const status = await fetchFigmaStatus();
          get().applyStatus(status);
          return status;
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "无法访问 Figma 接口";
          set({
            connectionState: "error",
            linked: false,
            statusMessage: message,
          });
          throw error;
        }
      },

      disconnect: () => {
        set({
          linked: false,
          connectionState: "idle",
          statusMessage: "已断开，可重新连接 Figma MCP",
          tools: [],
        });
      },
    }),
    {
      name: "zood-figma-prefs",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        linked: state.linked,
        mode: state.mode,
        mcpUrl: state.mcpUrl,
      }),
    },
  ),
);
