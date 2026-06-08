import type { StreamEventType } from "@/types/api";

/** 会从 SSE 事件中提取 Sandpack 文件内容的步骤 */
export const CODE_FILE_EVENT_TYPES = new Set<StreamEventType>([
  "types",
  "utils",
  "mockData",
  "service",
  "hooks",
  "componentsCode",
  "pagesCode",
  "layouts",
  "styles",
  "app",
  "files",
  "figmaAssembly",
  "figmaComponentGen",
]);

function normalizeSandpackPath(path: string): string {
  let normalized = path.replace(/\\/g, "/");
  if (!normalized.startsWith("/")) {
    normalized = `/${normalized}`;
  }
  if (normalized.startsWith("/src/")) {
    normalized = normalized.slice(4);
  }
  return normalized;
}

function addFile(
  result: Record<string, string>,
  path: string | undefined,
  content: string | undefined,
) {
  if (!path || !content) return;
  result[normalizeSandpackPath(path)] = content;
}

function addFromFileList(
  result: Record<string, string>,
  files: unknown,
  codeKeys: string[] = ["content", "code"],
) {
  if (!Array.isArray(files)) return;

  for (const item of files) {
    if (!item || typeof item !== "object") continue;
    const record = item as Record<string, string>;
    const content = codeKeys.map((key) => record[key]).find(Boolean);
    addFile(result, record.path, content);
  }
}

/**
 * 从 SSE 事件 payload 中提取可写入 Sandpack 的文件映射
 */
export function extractSandpackFilesFromEvent(
  type: string,
  data: unknown,
): Record<string, string> {
  const result: Record<string, string> = {};
  if (!data) return result;

  switch (type) {
    case "types":
    case "utils":
      addFromFileList(result, (data as { files?: unknown }).files, ["code", "content"]);
      break;

    case "mockData":
    case "service":
    case "hooks":
      addFromFileList(result, (data as { files?: unknown }).files);
      break;

    case "componentsCode":
    case "pagesCode":
      if (Array.isArray(data)) {
        addFromFileList(result, data);
      } else {
        addFromFileList(result, (data as { files?: unknown }).files);
      }
      break;

    case "layouts":
      addFromFileList(result, (data as { layoutsCode?: unknown }).layoutsCode);
      break;

    case "styles":
    case "app": {
      const record = data as { path?: string; content?: string };
      addFile(result, record.path, record.content);
      break;
    }

    case "files":
    case "figmaAssembly": {
      const filesMap = (data as { files?: Record<string, string> }).files;
      if (filesMap) {
        for (const [path, code] of Object.entries(filesMap)) {
          addFile(result, path, code);
        }
      }
      break;
    }

    case "figmaComponentGen":
      if (Array.isArray(data)) {
        addFromFileList(result, data);
      } else if (typeof data === "object") {
        const record = data as {
          files?: unknown;
          generatedFiles?: unknown;
        };
        addFromFileList(result, record.files ?? record.generatedFiles);
      }
      break;

    default:
      break;
  }

  return result;
}

export function isCodeFileEvent(type: string): boolean {
  return CODE_FILE_EVENT_TYPES.has(type as StreamEventType);
}
