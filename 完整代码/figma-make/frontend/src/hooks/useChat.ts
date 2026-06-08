// 聊天相关自定义 Hook
"use client";

import { useCallback } from "react";
import { ChatMessage } from "@/types/message";
import { generateAppStream } from "@/services/api";
import { useChatStore } from "@/store/chatStore";
import { useSandpackStore } from "@/store/sandpackStore";
import { useSupabaseStore } from "@/store/supabaseStore";
import { StreamEventType } from "@/types/api";
import type { FlowType } from "@/types/flow";
import { isFigmaUrl } from "@/types/flow";
import {
  FLOW_CONFIG,
  NEXT_STEP_MAP,
  STEP_DEFINITIONS,
  getPhaseByNode,
} from "@/constants/chat";
import {
  extractSandpackFilesFromEvent,
  isCodeFileEvent,
} from "@/lib/sandpackFromEvent";
import {
  conversationalAnalysisDescription,
  isConversationalAnalysis,
  isDatabaseInquiryAnalysis,
  isTrivialChitChatMessage,
} from "@/lib/chitChat";
import { supabaseThoughtPayload } from "@/lib/supabaseThoughtPayload";

/** 这些步骤的 payload 体积大，写入 thought.content 会导致聊天区卡顿 */
const THOUGHT_LIGHT_CONTENT_ONLY = new Set<StreamEventType>([
  "componentsCode",
  "pagesCode",
  "layouts",
  "styles",
  "types",
  "utils",
  "mockData",
  "service",
  "hooks",
  "supabase",
  "inquiry",
  "files",
  "figmaAssembly",
  "figmaComponentGen",
]);

function thoughtContentForStep(
  type: StreamEventType,
  data: unknown,
): string | undefined {
  if (THOUGHT_LIGHT_CONTENT_ONLY.has(type)) return undefined;
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return undefined;
  }
}

/**
 * useChat
 *
 * Chat 领域唯一入口
 * - 管理消息状态
 * - 触发生成
 * - 维护 loading / streaming
 * - 接收 files 事件并更新 Sandpack
 */
export function useChat() {
  const {
    messages,
    isLoading,
    addMessage,
    setLoading,
    addThought,
    updateThought,
    finalizeConversationalThoughts,
    archiveThoughts,
    updatePhaseProgress,
    collapsePhase,
    updateProjectName, // 获取更新项目名称的方法
    incrementVersion, // 递增版本号
    getCurrentThreadId, // 获取当前版本的 threadId
    saveVersion, // 保存版本快照
    setCurrentFlow, // 设置当前流程类型
  } = useChatStore();

  const {
    applyAssembledFiles,
    setIsAssembling,
    startGeneration,
    mergeGeneratedFiles,
    updateGenerationStep,
    finishGeneration,
    completeGeneration,
    setViewMode,
    generatedFiles,
    generatedFileCount,
  } = useSandpackStore();

  const getThoughtDetails = (
    type: StreamEventType,
    status: "pending" | "success" | "error",
    data?: unknown,
  ) => {
    const config = STEP_DEFINITIONS[type];

    if (!config) {
      return {
        title: "处理中",
        description: "AI 正在思考...",
      };
    }

    let descriptionStr = "";
    if (status === "pending") {
      descriptionStr = config.description.pending;
    } else {
      const successDesc = config.description.success;
      descriptionStr =
        typeof successDesc === "function" ? successDesc(data) : successDesc;
    }

    return {
      title: config.title,
      description: descriptionStr,
    };
  };

  /**
   * 发送用户消息，并触发 AI 生成
   */
  const sendMessage = useCallback(
    async (content: string, attachments?: { type: "image"; url: string }[]) => {
      // Guard: 防止重复提交
      if (useChatStore.getState().isLoading) return;

      // 版本管理：判断是创建还是编辑
      const isEditing = messages.some((m) => m.role === "assistant");
      const operation: "create" | "edit" = isEditing ? "edit" : "create";

      // 递增版本号
      const newVersion = incrementVersion();
      const threadId = getCurrentThreadId();

      console.log(
        `[useChat] ${operation === "create" ? "Creating" : "Editing"} project:`,
        {
          version: newVersion,
          threadId,
          operation,
        },
      );

      // 1. 构造并添加用户消息
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        attachments,
      };

      // 获取当前完整的消息历史 (Store中的 + 当前这一条)
      const currentHistory = [...useChatStore.getState().messages, userMessage];

      addMessage(userMessage);

      // 2. 初始化状态
      setLoading(true);

      // ✨ 归档上一次的思维链（找到最后一个 assistant 消息）
      const previousMessages = useChatStore.getState().messages;
      const lastAssistantMsg = [...previousMessages]
        .reverse()
        .find((m) => m.role === "assistant");
      if (lastAssistantMsg) {
        archiveThoughts(lastAssistantMsg.id);
      }

      // ✨ 立即创建一个 assistant 消息来承载思维链
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "", // 内容后续通过 streaming 填充
      };
      const assistantId = assistantMessage.id; // ✨ 保存 ID 用于后续操作
      addMessage(assistantMessage);

      // ✨ 流程类型识别：检测用户输入是否包含 Figma 链接
      const existingFilesPayload =
        operation === "edit" && generatedFiles
          ? Object.fromEntries(
              Object.entries(generatedFiles).map(([path, file]) => [
                path,
                file.code,
              ]),
            )
          : undefined;

      const supabaseToggle = useSupabaseStore.getState().enabled;
      const wantsSupabase =
        supabaseToggle ||
        /\bsupabase\b|数据库|postgres|后端\s*api/i.test(content);

      const flowType: FlowType = isFigmaUrl(content)
        ? "figma"
        : operation === "edit" &&
            generatedFileCount > 0 &&
            existingFilesPayload
          ? "modification"
          : "traditional";
      setCurrentFlow(flowType);

      // ✨ 使用流程配置的初始步骤
      const initialType = FLOW_CONFIG[flowType].initialStep;

      console.log(`[useChat] Flow: ${flowType}, Initial Step: ${initialType}`);

      const initialDetails = getThoughtDetails(
        initialType as StreamEventType,
        "pending",
      );
      const initialPhase = getPhaseByNode(initialType as StreamEventType);
      addThought(assistantId, {
        // 传入 messageId
        key: initialType,
        type: "node", // 标记为节点级
        phase: initialPhase,
        title: initialDetails.title,
        description: initialDetails.description,
        status: "pending",
      });

      // 启动 Sandpack 流式生成会话
      startGeneration(threadId);
      let hasSwitchedToCode = false;

      try {
        // 3. 调用流式接口，传递版本化的 threadId
        await generateAppStream(
          {
            messages: currentHistory,
            projectId: threadId,
            files: existingFilesPayload,
            useSupabase: wantsSupabase || undefined,
          },
          (event) => {
            const { type, data } = event;
            console.log("[useChat] Stream Event:", type);

            if (type === "done") return;

            if (type === "error") {
              const payload = data as { message?: string };
              const hasFiles =
                (useSandpackStore.getState().generatedFileCount ?? 0) > 0;
              addThought(assistantId, {
                key: `error-${Date.now()}`,
                title: hasFiles ? "编译检查未通过" : "发生错误",
                description: payload.message || "未知错误",
                status: hasFiles ? "success" : "error",
              });
              if (hasFiles) {
                setViewMode("preview");
                completeGeneration();
              } else {
                finishGeneration();
              }
              return;
            }

            // 闲聊 / 问答 / 数据库探查：直接展示回复
            if (type === "chatReply") {
              const payload = data as {
                message?: string;
                inquiry?: unknown;
              };

              if (payload.message) {
                useChatStore.setState((state) => ({
                  messages: state.messages.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: payload.message! }
                      : m,
                  ),
                }));
              }

              if (payload.inquiry) {
                const replyDetails = getThoughtDetails("chatReply", "success", data);
                updateThought(assistantId, "chatReply", {
                  title: replyDetails.title,
                  description: replyDetails.description,
                  status: "success",
                  content: payload.message,
                  payload: data,
                });
                finishGeneration();
                return;
              }

              const thoughts =
                useChatStore.getState().messageThoughts[assistantId] || [];
              const analysisThought = thoughts.find((t) => t.key === "analysis");
              let analysisDesc = conversationalAnalysisDescription({
                type: "CHIT_CHAT",
              });
              if (analysisThought?.content) {
                try {
                  const parsed = JSON.parse(
                    String(analysisThought.content),
                  ) as unknown;
                  if (
                    isConversationalAnalysis(parsed) ||
                    isDatabaseInquiryAnalysis(parsed)
                  ) {
                    analysisDesc = conversationalAnalysisDescription(parsed);
                  }
                } catch {
                  /* ignore */
                }
              } else if (isTrivialChitChatMessage(content)) {
                analysisDesc = conversationalAnalysisDescription({
                  type: "CHIT_CHAT",
                });
              }

              finalizeConversationalThoughts(assistantId, {
                analysisDescription: analysisDesc,
                replyMessage: payload.message,
              });

              finishGeneration();
              return;
            }

            const stepDetails = getThoughtDetails(
              type as StreamEventType,
              "success",
              data,
            );
            updateGenerationStep(type, stepDetails.title);

            const isFinalFilesEvent = type === "files" || type === "figmaAssembly";

            // 增量合并代码文件到 Sandpack。最终全量 files 事件单独覆盖，避免重复同步/刷新。
            if (isCodeFileEvent(type) && !isFinalFilesEvent) {
              const partialFiles = extractSandpackFilesFromEvent(type, data);
              const fileCount = Object.keys(partialFiles).length;

              if (fileCount > 0) {
                console.log(
                  `[useChat] Merging ${fileCount} files from event:`,
                  type,
                );
                mergeGeneratedFiles(partialFiles, {
                  step: type,
                  stepTitle: stepDetails.title,
                });

                if (!hasSwitchedToCode) {
                  setViewMode("code");
                  hasSwitchedToCode = true;
                }
              }
            }

            // 最终 files 事件：全量覆盖并保存版本
            if (isFinalFilesEvent) {
              const filesPayload = data as {
                files?: Record<string, string>;
                stats?: { compileError?: string; compileChecked?: boolean };
              };
              if (filesPayload.files) {
                console.log(
                  "[useChat] Final generated files:",
                  Object.keys(filesPayload.files).length,
                );
                const compileDone =
                  filesPayload.stats?.compileChecked !== undefined;
                applyAssembledFiles(filesPayload.files, {
                  compileChecked: filesPayload.stats?.compileChecked,
                });

                saveVersion({
                  versionNumber: newVersion,
                  threadId: threadId,
                  operation: operation,
                  prompt: content,
                  timestamp: Date.now(),
                  files: filesPayload.files,
                  fileCount: Object.keys(filesPayload.files).length,
                  changes: undefined,
                });

                console.log("[useChat] Version saved:", {
                  version: newVersion,
                  operation,
                  fileCount: Object.keys(filesPayload.files).length,
                });

                if (filesPayload.stats?.compileError) {
                  addThought(assistantId, {
                    key: `compile-warn-${Date.now()}`,
                    title: "编译检查未通过",
                    description:
                      "代码已加载到预览，但本地构建有告警。可在代码视图中修改后重试。",
                    status: "success",
                  });
                }

                // 组装/后处理：只同步文件；编译检查结束后再 remount 预览
                setViewMode("preview");
                if (compileDone) {
                  console.log(
                    "[useChat] Preview remount after compile:",
                    filesPayload.stats?.compileChecked,
                  );
                }
              }
            }

            // 特殊处理：intent 事件 - 更新项目名称
            if (type === "intent") {
              const intentPayload = data as {
                product?: { name?: string };
              };
              if (intentPayload.product?.name) {
                console.log(
                  "[useChat] Updating project name:",
                  intentPayload.product.name,
                );
                updateProjectName(intentPayload.product.name);
              }
            }

            // 核心逻辑修正：
            // 收到 event type (如 "analysis") 代表该步骤已完成
            // 1. 更新当前步骤为完成
            // 2. 开启下一个步骤为 pending

            const isDbInquiry =
              type === "analysis" && isDatabaseInquiryAnalysis(data);

            const skipPipeline =
              type === "analysis" &&
              (isConversationalAnalysis(data) ||
                isTrivialChitChatMessage(content));

            const currentStepDetails = getThoughtDetails(
              type as StreamEventType,
              "success",
              data,
            );

            const stepDescription =
              type === "analysis" && (skipPipeline || isDbInquiry)
                ? conversationalAnalysisDescription(data)
                : currentStepDetails.description;

            const toolPayload = supabaseThoughtPayload(
              type as StreamEventType,
              data,
            );

            // 更新当前步骤状态
            updateThought(assistantId, type, {
              status: "success",
              description: stepDescription,
              content: thoughtContentForStep(type as StreamEventType, data),
              ...(toolPayload !== undefined ? { payload: toolPayload } : {}),
            });

            // 阶段聚合逻辑：更新阶段进度并检测是否需要折叠
            const currentPhase = getPhaseByNode(type as StreamEventType);
            if (currentPhase && !skipPipeline) {
              updatePhaseProgress(currentPhase);

              const phaseInfo =
                useChatStore.getState().phaseCompletion[currentPhase];
              if (phaseInfo && phaseInfo.completed === phaseInfo.total) {
                collapsePhase(assistantId, currentPhase);
              }
            }

            // 闲聊/问答：不排队 intent；数据库探查：排队 supabase → inquiry
            if (isDbInquiry) {
              const supabasePending = getThoughtDetails("supabase", "pending");
              addThought(assistantId, {
                key: "supabase",
                type: "node",
                phase: getPhaseByNode("supabase"),
                title: supabasePending.title,
                description: supabasePending.description,
                status: "pending",
              });
              const inquiryPending = getThoughtDetails("inquiry", "pending");
              addThought(assistantId, {
                key: "inquiry",
                type: "node",
                phase: getPhaseByNode("inquiry"),
                title: inquiryPending.title,
                description: inquiryPending.description,
                status: "pending",
              });
              const replyPending = getThoughtDetails("chatReply", "pending");
              addThought(assistantId, {
                key: "chatReply",
                type: "node",
                phase: getPhaseByNode("analysis"),
                title: replyPending.title,
                description: replyPending.description,
                status: "pending",
              });
              return;
            }

            if (skipPipeline) {
              return;
            }

            // 查找并启动下一个步骤
            const nextType = NEXT_STEP_MAP[type];
            if (nextType && nextType !== "done") {
              // 如果下一个步骤是 app（应用组装），设置组装状态
              if (nextType === "app") {
                setIsAssembling(true);
              }

              const nextDetails = getThoughtDetails(
                nextType as StreamEventType,
                "pending",
              );
              const nextPhase = getPhaseByNode(nextType as StreamEventType);
              addThought(assistantId, {
                // ✨ 传入 messageId
                key: nextType,
                type: "node", // 标记为节点级
                phase: nextPhase,
                title: nextDetails.title,
                description: nextDetails.description,
                status: "pending",
              });
            }
          },
        );
      } catch (error) {
        console.error("Generate App Error:", error);
        addThought(assistantId, {
          // ✨ 传入 messageId
          key: `error-${Date.now()}`,
          title: "发生错误",
          description: error instanceof Error ? error.message : "未知错误",
          status: "error",
        });
      } finally {
        setLoading(false);
        finishGeneration();
      }
    },
    [
      addMessage,
      setLoading,
      archiveThoughts,
      addThought,
      updateThought,
      finalizeConversationalThoughts,
      updatePhaseProgress,
      collapsePhase,
      applyAssembledFiles,
      setIsAssembling,
      startGeneration,
      mergeGeneratedFiles,
      updateGenerationStep,
      finishGeneration,
      completeGeneration,
      setViewMode,
      messages, // 用于判断是否为编辑操作
      incrementVersion, // 版本管理
      getCurrentThreadId, // 版本管理
      saveVersion, // 版本管理
      updateProjectName, // 项目名称更新
      setCurrentFlow, // 流程类型设置
    ],
  );

  return {
    messages,
    isLoading,
    sendMessage,
  };
}
