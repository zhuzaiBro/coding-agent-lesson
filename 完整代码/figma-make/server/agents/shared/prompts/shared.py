"""
各 Agent 节点复用的共享 Prompt 片段。
"""

JSON_SAFETY_PROMPT = """
【JSON 输出安全规则 — 必须严格遵守】
0. **纯 JSON 输出**：只输出 JSON 数据本身，JSON 前后不得有任何文字、说明、markdown 代码块标记或注释。
1. 输出必须是可被 JSON.parse() 正确解析的合法 JSON。
2. 所有字符串值必须用双引号（"）包裹，禁止使用单引号。
3. 对象最后一个属性后不得有尾随逗号。
4. 数组最后一个元素后不得有尾随逗号。
5. 所有括号必须正确配对：{ } 与 [ ] 必须成对出现。
6. 字符串内的特殊字符必须正确转义：
   - 换行使用 \\n
   - 双引号使用 \\"
   - 反斜杠使用 \\\\
   - 制表符使用 \\t
7. JSON 中不得包含注释（// 或 /* */）。
8. 数值类型不得加引号，布尔值使用小写 true/false。
9. 生成后请在心中校验 JSON 结构完整性。
"""


IMPORT_PATH_CONSTRAINT_PROMPT = """
【导入与依赖约束 — 必须遵守，无例外】
1. **禁止虚构模块**：不得 import 用户消息中「可用文件」或「导入清单」未列出的文件、别名或 npm 包。
2. **路径必须精确**：import 路径必须能解析到已列出的文件，不得猜测名称（例如未列出 `/services/todoItemService.ts` 时不得使用 `todoItemService`）。
3. **相对路径**（除项目已使用的 shadcn `/components/ui/*` 外，不使用 `@/`）：
   - 从 `/hooks/X.ts` → `../services/<serviceBasename>` 与 `../types/<typeBasename>`
   - 从 `/services/X.ts` → `../data/<dataBasename>` 与 `../types/<typeBasename>`
   - 从 `/pages/X.tsx` → `../hooks/<hookBasename>`、`../components/<name>`
   - import 路径中省略 `.ts` / `.tsx` 扩展名。
4. **配对命名**：一个 mock 数据文件 ↔ 一个 service 文件 ↔ 一个 hook 文件。
   - Mock: `/data/todoItems.ts` → Service: `/services/todoItemService.ts` → Hook: `/hooks/useTodoItems.ts`
   - Service 基名必须为 `{modelCamel}Service`；Hook 必须为 `use{ModelPascal}` 并 import 该 service。
5. **最小范围**：只实现规格要求的内容，不额外添加文件、helper、store 或抽象层。
6. **禁止投机代码**：不得有占位 import、`// TODO` 桩代码，或引用不存在模块的死代码路径。
"""


EXPORT_STYLE_CONSTRAINT_PROMPT = """
【导出/导入风格 — 项目级约定】
React 组件（components、pages、layouts）使用 **default export**；非 UI 模块（services、hooks、types、mock data、utils）使用 **named export**。

1. **组件与页面文件**（`/components/*.tsx`、`/pages/*.tsx`、`/layouts/*.tsx`）：
   - 必须以 `export default ComponentName;` 结尾。
   - default export 名称必须与文件基名一致（如 `/components/TodoTitleInput.tsx` → `export default TodoTitleInput;`）。
   - 组件不得仅使用 `export function X` / `export const X` 而无 `export default`。

2. **导入组件/页面**：
   - 必须使用 default import：`import TodoTitleInput from '../components/TodoTitleInput';`
   - 除非库明确提供 named export，否则不得对组件文件使用 `import { TodoTitleInput } from '...'`。

3. **Hooks、Services、Types、Data**：
   - 仅使用 named export：`export async function getAllTodos`、`export function useTodos`、`export interface Todo`。
   - 使用花括号导入：`import { getAllTodos } from '../services/todoItemsService';`
   - **Services**：只导出独立 async 函数，不得 `export class TodoItemService`，不得 `export const TodoItemService = {{...}}`，不得将文件名作为符号导出。
   - **Hooks**：只 import「Service export catalog → allowedSymbols」中列出的符号，禁止 `import {{ TodoItemService }}` 或与 service 文件名匹配的 `import {{ XxxService }}`。

4. **输出前一致性检查**：
   - 每个 `import X from '../components/...'` 的目标文件必须包含 `export default X`（或该符号的 default export）。
   - 同一符号不得混用风格（不得仅 `export const Foo` 却在别处 `import Foo from`）。
   - 输出前对照用户消息中的 export 清单，每个 `import {{ ... }}` 的符号必须出现在对应文件的 `namedExports` 列表中。
"""


MANIFEST_DSL_PROMPT = """
【项目 Manifest DSL — 当用户消息中提供时】
1. 将 `modules[]` 作为路径与导出的唯一真相来源。
2. 每个 module：`namedExports` 用于 `import {{ ... }}`，`defaultExport` + `importForms.default.example` 用于 default import。
3. 不得 import `module.namedExports` 或 `module.defaultExport` 未列出的符号。
4. 生成 App.tsx 时使用 `importForms.fromApp` 作为 import 路径。
5. 不得虚构 module、npm 包或 export 别名。
"""


def append_json_safety(prompt: str) -> str:
    """在已有 system prompt 末尾追加 JSON 安全规则。"""
    return f"{prompt}\n{JSON_SAFETY_PROMPT}"
