# zood-figma-make-server


---

## 技术栈

| 层级 |  Python 版 |
|------|-----------|
| Web 框架 |   **FastAPI** |
| SSE 流式 | **sse-starlette** |
| Agent 编排 | **LangGraph Python** |
| Schema 验证 | **Pydantic v2** |
| 对象存储 | **oss2** |
| Figma MCP | **httpx JSON-RPC** |
| 包管理 | **uv** |

---

## 目录结构

```
server-py/
├── main.py                         # FastAPI 应用入口（含 CORS、路由挂载）
├── pyproject.toml                  # uv 项目配置 & 依赖声明
├── .env.example                    # 环境变量模板
│
├── config/
│   ├── chat.py                     # 节点名 → SSE 事件类型映射表
│   ├── mock.py                     # 分层 Mock 配置（global/phases/nodes）
│   └── oss.py                      # 阿里云 OSS 连接配置
│
├── routes/
│   ├── index.py                    # GET /
│   ├── template.py                 # GET /api/template/react-ts
│   ├── chat.py                     # POST /api/chat（SSE 流式）
│   └── upload.py                   # POST /api/upload/image
│
├── agents/
│   ├── adapters/                   # 路由分流适配器（决定走哪条生成流程）
│   │   ├── route_registry.py       # 适配器注册表（按优先级首次匹配）
│   │   ├── figma_adapter.py        # Figma URL → figma 流程（优先级 100）
│   │   ├── modification_adapter.py # 修改关键词 → traditional（优先级 90）
│   │   ├── image_adapter.py        # 图片附件 → traditional（优先级 80）
│   │   └── prompt_adapter.py       # 纯文本 → traditional（优先级 70）
│   │
│   ├── graphs/
│   │   ├── main_graph.py           # 工厂函数 build_agent(mode)
│   │   ├── traditional_graph.py    # 传统 19 节点串行流水线
│   │   ├── figma_graph.py          # Figma 直连 9 节点流水线
│   │   ├── component_graph.py      # 组件并行生成子图（fan-out）
│   │   └── page_graph.py           # 页面并行生成子图（fan-out）
│   │
│   ├── flows/
│   │   ├── traditional/            # 传统流程节点（prompt 驱动）
│   │   │   ├── input_processing/   # Step 1: 意图理解
│   │   │   ├── analysis/           # Step 0/2-4: 需求分析 → 能力/UI/组件规格
│   │   │   ├── architecture/       # Step 5-8: 项目结构/依赖/类型/布局
│   │   │   ├── code_generation/    # Step 9-13: utils/mock/service/hooks/样式
│   │   │   └── assembly/           # Step 14-16: App入口/文件组装/AST后处理
│   │   │
│   │   └── figma_direct/           # Figma 直连流程节点（MCP 驱动）
│   │       ├── input/              # Step 1-2: MCP 获取代码 + 图片 OSS 化
│   │       ├── parsing/            # Step 3-5: AST解析 + 布局提取 + 几何聚类
│   │       ├── refactoring/        # Step 6-7: AI 命名 + AI 组件生成（并行）
│   │       └── assembly/           # Step 8-9: 组装 Sandpack + AST 后处理
│   │
│   ├── shared/
│   │   ├── prompts/shared.py       # JSON 安全输出规则（各节点复用）
│   │   ├── schemas/graph_schema.py # 主图完整 State 定义
│   │   └── utils/figma_url.py      # Figma URL 正则检测（单一来源）
│   │
│   └── utils/
│       ├── model.py                # 模型单例（DeepSeek / GLM / Qwen-VL）
│       ├── mock.py                 # Mock 策略执行器
│       ├── retry.py                # LLM 调用重试器（带错误反馈）
│       ├── code_normalizer.py      # 转义字符修复（LLM 常见输出问题）
│       ├── dependency_builder.py   # 读取模板 package.json / import 扫描
│       ├── frontend_compile.py     # 临时 Vite 项目真实编译校验
│       ├── ast/fixer.py            # AST 后处理（对象渲染/安全访问修复）
│       └── export_repair.py        # export/import 确定性修复
│
│   # assembly/nodes/debug_fix_node.py — 编译失败时 LLM 自动修文件（可配置重试）
│
├── services/
│   ├── figma/mcp_client.py         # Figma Desktop MCP HTTP 客户端
│   └── supabase/mcp_client.py      # Supabase Remote MCP HTTP 客户端
│
└── utils/
    └── oss.py                      # 阿里云 OSS 上传工具（单例 Bucket）
```

---

## 快速开始

### 1. 安装依赖

```bash
# 需要 Python ≥ 3.11，uv 已安装
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入以下必填项：
#   DEEPSEEK_API_KEY 或 GLM_API_KEY（主模型）
#   ALI_OSS_AK / ALI_OSS_SK / ALI_OSS_BUCKET（图片上传）
#   FIGMA_MCP_URL（Figma 流程，默认 http://127.0.0.1:3845/mcp）
```

### 3. 启动服务

```bash
# 直接运行
uv run python main.py

# 热重载模式（开发推荐）
uv run uvicorn main:app --reload --port 7001
```

服务启动后访问 `http://localhost:7001`。

---

## API 接口

### `GET /`
健康检查，返回欢迎文字。

### `GET /api/template/react-ts`
返回 `templates/react-ts/` 目录下所有文件内容，供前端 Sandpack 初始化使用。

**响应格式：**
```json
{
  "/src/main.tsx": { "code": "..." },
  "/package.json": { "code": "..." }
}
```

### `POST /api/chat`
核心接口，SSE 流式返回代码生成进度。

**请求体：**
```json
{
  "messages": [...],
  "projectId": "project-xxx",
  "mockConfig": { "global": false }
}
```

**SSE 事件格式：**
```
data: {"type": "analysis", "data": {...}}
data: {"type": "files",    "data": {...}}
data: {"type": "done"}
data: {"type": "error",    "message": "..."}
```

**路由分流规则（按优先级）：**
| 条件 | 流程 | 优先级 |
|------|------|--------|
| 消息含 Figma URL | figma 流程 | 100 |
| 消息含修改关键词 | traditional 流程 | 90 |
| 消息含图片附件 | traditional 流程 | 80 |
| 消息含纯文本 | traditional 流程 | 70 |
| 兜底 | traditional 流程 | 10 |

### `POST /api/upload/image`
上传图片到阿里云 OSS，返回公网可访问链接。

- 支持格式：`.jpg .jpeg .png .gif .webp .svg`
- 最大文件：10MB
- 字段名：`file`（multipart/form-data）

**响应：**
```json
{ "url": "https://bucket.endpoint/images/xxx.png", "name": "filename.png" }
```

---

## 两种生成流程

### 传统流程（Traditional）
> 适用于文字描述、图片参考、修改请求

20 个节点串行推进，每个节点完成后立即推送 SSE 事件：

```
analysisNode → intentNode → capabilityNode → uiNode → componentNode
→ structureNode → dependencyNode → typeNode → utilsNode → mockDataNode
→ serviceNode → hooksNode → componentSubgraph(并行) → pageSubgraph(并行)
→ layoutNode → styleGenNode → appGenNode → assembleNode → postProcessNode
→ compileCheckNode
```

### Figma 直连流程（Figma Direct）
> 适用于消息中包含 Figma 设计稿链接

10 个节点流水线，MCP 一次性拿到设计稿代码后逐步拆解重构：

```
figmaInputNode → imageDownloadNode → astParserNode → blockExtractNode
→ geometryGroupNode → sectionNamingNode → componentGenNode
→ assemblyNode → figmaPostProcessNode → figmaCompileCheckNode
```

---

## Mock 模式

用于跳过 LLM 调用、使用本地 `mock/*.json` 数据加速调试。

在 `.env` 中设置全局开关：
```env
MOCK_MODE=true
```

或在请求体中按节点/阶段精细控制：
```json
{
  "mockConfig": {
    "global": false,
    "phases": { "planning": true },
    "nodes": { "styleGenNode": true }
  }
}
```

**优先级：** `nodes` > `phases` > `global` > `MOCK_MODE` 环境变量

---

## 切换主模型

通过环境变量选择：
```env
# 使用 DeepSeek（默认）
MAIN_MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx

# 使用智谱 GLM
MAIN_MODEL_PROVIDER=glm
GLM_API_KEY=xxx

# 使用通义千问（DashScope 兼容 OpenAI 接口）
MAIN_MODEL_PROVIDER=qwen
QWEN_API_KEY=sk-xxx
QWEN_TEXT_MODEL=qwen-plus
QWEN_VL_MODEL=qwen-vl-max
```

主模型为 `qwen` 时使用 `QWEN_TEXT_MODEL`（如 `qwen-plus`、`qwen-max`）；勿将 `qwen-vl-*` 设为主模型。请保持 `QWEN_ENABLE_THINKING=false`，否则 DashScope 思考模式不支持 `tool_choice=required`（流水线会自动降级为 JSON prompt 解析）。视觉分析节点使用 `QWEN_VL_MODEL`，需配置 `QWEN_API_KEY`。

---

## Supabase MCP 配置

服务端通过 [Supabase Remote MCP](https://supabase.com/docs/guides/ai-tools/mcp) 拉取真实表结构，并注入 Traditional 流水线的 `serviceNode` / `hooksNode` 提示词。

1. 在 [Supabase Access Tokens](https://supabase.com/dashboard/account/tokens) 创建 PAT
2. 在 Dashboard → Project Settings → General 复制 **Project ID**（即 `project_ref`）
3. 写入 `server/.env`：

```bash
SUPABASE_ACCESS_TOKEN=your_pat
SUPABASE_PROJECT_REF=your_project_ref
SUPABASE_MCP_READ_ONLY=true   # 推荐：仅查询，禁止 DDL
```

4. 重启服务后验证：

```bash
curl http://localhost:7001/api/supabase/status
curl http://localhost:7001/api/supabase/schema
```

`analysisNode` 会由 LLM 结构化输出 `needsDatabase`（是否需联调真实数据库）；为 true 或请求体 `useSupabase: true` 时，`supabaseSubgraph`（connect → config → schema → types）自动连接 MCP。

本地 Supabase CLI 可使用 `SUPABASE_MCP_URL=http://127.0.0.1:54321/mcp`（无需 PAT）。

---

## Figma MCP 配置

Figma 流程依赖本机运行的 Figma Desktop MCP Server：

1. 安装并打开 Figma Desktop
2. 在 Figma Desktop 中登录并打开目标设计文件
3. 确保 MCP Server 监听在 `http://127.0.0.1:3845/mcp`（Figma Desktop 自动启动）
4. 在消息中粘贴 Figma 设计稿链接即可触发 figma 流程

---

## 开发说明

```bash
# 代码检查
uv run ruff check .

# 格式化
uv run ruff format .
```

Python ≥ 3.11 required（使用了 `match`、`TypeAlias`、`Self` 等新特性语法）。
