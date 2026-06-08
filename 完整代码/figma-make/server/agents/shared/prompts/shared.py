"""
Shared prompt fragments for reuse across agent nodes.
"""

JSON_SAFETY_PROMPT = """
【JSON Output Safety Rules - Must Strictly Follow】
0. **Pure JSON output**: Only output JSON data itself. No text, explanations, markdown code block markers, or comments before or after the JSON.
1. Output must be strictly valid JSON format that can be correctly parsed by JSON.parse().
2. All string values must be wrapped in double quotes ("). Single quotes are forbidden.
3. No trailing comma after the last property of an object.
4. No trailing comma after the last element of an array.
5. All brackets must be correctly paired: { } and [ ] must appear in pairs.
6. Special characters within strings must be correctly escaped:
   - Newlines use \\n
   - Double quotes use \\"
   - Backslashes use \\\\
   - Tabs use \\t
7. No comments in JSON (// or /* */).
8. Numeric types must not be wrapped in quotes, booleans use true/false (lowercase).
9. After generation, mentally validate the completeness of the JSON structure.
"""


IMPORT_PATH_CONSTRAINT_PROMPT = """
【Import & dependency constraints — MUST follow, no exceptions】
1. **No invented modules**: Never import a file, alias, or npm package that is not listed in the user message under "Available files" or "Import manifest".
2. **Exact paths only**: Import paths must resolve to a listed file. Do not guess names (e.g. do NOT use `todoItemService` unless `/services/todoItemService.ts` is listed).
3. **Relative imports** (no `@/` except shadcn `/components/ui/*` when already used in project):
   - From `/hooks/X.ts` → `../services/<serviceBasename>` and `../types/<typeBasename>`
   - From `/services/X.ts` → `../data/<dataBasename>` and `../types/<typeBasename>`
   - From `/pages/X.tsx` → `../hooks/<hookBasename>`, `../components/<name>`
   - Omit `.ts` / `.tsx` extensions in import specifiers.
4. **Paired naming**: One mock data file ↔ one service file ↔ one hook file.
   - Mock: `/data/todoItems.ts` → Service: `/services/todoItemService.ts` → Hook: `/hooks/useTodoItems.ts`
   - Service basename must be `{modelCamel}Service`; hook must be `use{ModelPascal}` importing that exact service.
5. **Minimal scope**: Implement only what the specification requires. No extra files, helpers, stores, or abstractions.
6. **No speculative code**: No placeholder imports, no `// TODO` stubs, no dead code paths referencing missing modules.
"""

EXPORT_STYLE_CONSTRAINT_PROMPT = """
【Export / import style — project-wide convention】
Use **default export** for React components (components, pages, layouts). Use **named exports** for non-UI modules (services, hooks, types, mock data, utils).

1. **Component & page files** (`/components/*.tsx`, `/pages/*.tsx`, `/layouts/*.tsx`):
   - MUST end with: `export default ComponentName;`
   - The default export name MUST match the file basename (e.g. `/components/TodoTitleInput.tsx` → `export default TodoTitleInput;`).
   - Do NOT use only `export function X` / `export const X` without `export default` for components.

2. **Importing components/pages**:
   - MUST use default import: `import TodoTitleInput from '../components/TodoTitleInput';`
   - Do NOT use `import { TodoTitleInput } from '...'` for component files unless the library explicitly shows a named export.

3. **Hooks, services, types, data**:
   - Use named exports only: `export async function getAllTodos`, `export function useTodos`, `export interface Todo`.
   - Import with braces: `import { getAllTodos } from '../services/todoItemsService';`
   - **Services**: export standalone async functions only. Do NOT `export class TodoItemService`, do NOT `export const TodoItemService = {{...}}`, do NOT export the filename as a symbol.
   - **Hooks**: import ONLY symbols listed in "Service export catalog → allowedSymbols". Never `import {{ TodoItemService }}` or `import {{ XxxService }}` matching the service filename.

4. **Consistency check before output**:
   - Every `import X from '../components/...'` target file must contain `export default X` (or default export of that symbol).
   - Never mix styles on the same symbol (do not export both `export const Foo` only and expect `import Foo from` elsewhere).
   - Before emitting code, cross-check every `import {{ ... }}` against the user message export inventory; every symbol must appear in that file's `namedExports` list.
"""


MANIFEST_DSL_PROMPT = """
【Project Manifest DSL — when provided in the user message】
1. Treat `modules[]` as the only source of truth for paths and exports.
2. For each module: use `namedExports` for `import {{ ... }}`, use `defaultExport` + `importForms.default.example` for default imports.
3. Never import a symbol not listed in `module.namedExports` or `module.defaultExport`.
4. Use `importForms.fromApp` as the import specifier when generating App.tsx.
5. Do not invent modules, npm packages, or export aliases.
"""


def append_json_safety(prompt: str) -> str:
    """Append JSON safety prompt to an existing system prompt."""
    return f"{prompt}\n{JSON_SAFETY_PROMPT}"
