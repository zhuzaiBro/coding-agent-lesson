import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import {
  fetchSupabaseStatus,
  fetchSupabaseClientConfig,
  fetchSupabaseProjects,
  selectSupabaseProject,
  type SupabaseStatusResponse,
} from "@/services/supabaseApi";
import {
  buildSupabaseEnvFile,
  parseAnonKeyFromPublishableKeys,
} from "@/lib/supabaseEnv";
import { useSandpackStore } from "@/store/sandpackStore";

export type SupabaseConnectionState =
  | "idle"
  | "loading"
  | "connected"
  | "not_configured"
  | "error";

export type ConnectToAppResult = {
  ok: boolean;
  configured: boolean;
  message: string;
};

export interface SupabaseStore {
  /** 下一次生成是否带上 useSupabase */
  enabled: boolean;
  /** 已拉取 client-config 并注入 Sandpack */
  linked: boolean;
  anonKey: string | null;
  connectionState: SupabaseConnectionState;
  projectUrl: string | null;
  mcpUrl: string | null;
  statusMessage: string | null;
  lastCheckedAt: number | null;
  setEnabled: (enabled: boolean) => void;
  toggleEnabled: () => void;
  checkConnection: () => Promise<SupabaseStatusResponse>;
  applyStatus: (status: SupabaseStatusResponse) => void;
  /** 一键连接：检测 MCP → 拉取密钥 → 启用生成 → 写入应用 .env */
  connectToApp: () => Promise<ConnectToAppResult>;
  disconnectFromApp: () => void;
}

function mapStatus(status: SupabaseStatusResponse): {
  state: SupabaseConnectionState;
  message: string;
} {
  if (!status.configured) {
    return {
      state: "not_configured",
      message:
        status.message ??
        "请点击 Supabase 在浏览器完成 OAuth 授权",
    };
  }
  if (status.configured && status.schemaReady === false) {
    return {
      state: "error",
      message:
        status.message ??
        (status.needsProjectSelection
          ? "请选择要连接的 Supabase 项目（授权回调页会弹出列表）"
          : status.needsProjectRef
            ? "尚未绑定 Supabase 项目，请完成授权后选择项目"
            : "MCP 已授权但无法读取表结构，请检查 project_ref 与数据库权限"),
    };
  }
  if (status.ok && status.projectUrl) {
    return {
      state: "connected",
      message: `已连接：${status.projectUrl}`,
    };
  }
  if (status.ok) {
    return {
      state: "connected",
      message: "MCP 已连通",
    };
  }
  return {
    state: "error",
    message: status.message ?? "连接失败，请检查 PAT 与 project_ref",
  };
}

function injectEnvFiles(projectUrl: string, anonKey: string | null) {
  const content = buildSupabaseEnvFile(projectUrl, anonKey);
  useSandpackStore.getState().mergeGeneratedFiles({
    ".env": content,
    ".env.local": content,
  });
}

export const useSupabaseStore = create<SupabaseStore>()(
  persist(
    (set, get) => ({
      enabled: false,
      linked: false,
      anonKey: null,
      connectionState: "idle",
      projectUrl: null,
      mcpUrl: null,
      statusMessage: null,
      lastCheckedAt: null,

      setEnabled: (enabled) => set({ enabled }),

      toggleEnabled: () => set({ enabled: !get().enabled }),

      applyStatus: (status) => {
        const { state, message } = mapStatus(status);
        set({
          connectionState: state,
          projectUrl: status.projectUrl ?? get().projectUrl,
          mcpUrl: status.mcpUrl ?? null,
          statusMessage: message,
          lastCheckedAt: Date.now(),
        });
      },

      checkConnection: async () => {
        set({
          connectionState: "loading",
          statusMessage: "正在连接 Supabase MCP...",
        });
        try {
          const status = await fetchSupabaseStatus();
          get().applyStatus(status);
          return status;
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "无法访问 Supabase 接口";
          set({
            connectionState: "error",
            statusMessage: message,
            lastCheckedAt: Date.now(),
          });
          throw error;
        }
      },

      connectToApp: async () => {
        set({
          connectionState: "loading",
          statusMessage: "正在连接 Supabase 并配置应用...",
        });

        try {
          let status = await fetchSupabaseStatus();
          get().applyStatus(status);

          if (!status.configured) {
            return {
              ok: false,
              configured: false,
              message: get().statusMessage ?? "服务端未配置 Supabase",
            };
          }

          if (status.needsProjectSelection) {
            set({ statusMessage: "正在获取 Supabase 项目列表..." });
            const projects = await fetchSupabaseProjects();
            if (projects.length === 1) {
              await selectSupabaseProject(projects[0]);
              status = await fetchSupabaseStatus();
              get().applyStatus(status);
            } else if (projects.length > 1) {
              return {
                ok: false,
                configured: true,
                message:
                  "检测到多个 Supabase 项目，请在授权完成页选择要连接的项目后重试",
              };
            }
          }

          if (!status.ok || status.schemaReady === false) {
            return {
              ok: false,
              configured: true,
              message:
                get().statusMessage ??
                status.message ??
                "MCP 连接失败或未选择 Supabase 项目",
            };
          }

          const config = await fetchSupabaseClientConfig();
          const projectUrl = config.projectUrl?.trim() ?? status.projectUrl ?? "";
          const anonKey = parseAnonKeyFromPublishableKeys(
            config.publishableKeys ?? "",
          );

          if (projectUrl) {
            injectEnvFiles(projectUrl, anonKey);
          }

          const message = anonKey
            ? `Supabase 已连接到你的应用：${projectUrl}`
            : `已连接 ${projectUrl}（请在面板中确认 anon key）`;

          set({
            enabled: true,
            linked: true,
            anonKey,
            projectUrl,
            connectionState: "connected",
            statusMessage: message,
            lastCheckedAt: Date.now(),
          });

          return { ok: true, configured: true, message };
        } catch (error) {
          const message =
            error instanceof Error ? error.message : "连接 Supabase 失败";
          set({
            connectionState: "error",
            enabled: false,
            linked: false,
            statusMessage: message,
            lastCheckedAt: Date.now(),
          });
          return { ok: false, configured: true, message };
        }
      },

      disconnectFromApp: () => {
        set({
          enabled: false,
          linked: false,
          anonKey: null,
          statusMessage: "已断开，点击 Supabase 在浏览器重新授权",
          connectionState: "idle",
        });
      },
    }),
    {
      name: "zood-supabase-prefs",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        enabled: state.enabled,
        linked: state.linked,
        projectUrl: state.projectUrl,
        anonKey: state.anonKey,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.linked && state.projectUrl) {
          injectEnvFiles(state.projectUrl, state.anonKey);
        }
      },
    },
  ),
);
