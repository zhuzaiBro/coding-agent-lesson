import type { SandpackFiles } from "@/types/store";
import {
  LOCAL_SHIMMED_PACKAGES,
  patchPackageJsonForSandpack,
} from "./sandpackDependencies";

const TAILWIND_CDN_SCRIPT =
  '<script src="https://cdn.tailwindcss.com"></script>';

const DEFAULT_VITE_INDEX_HTML = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Preview</title>
    ${TAILWIND_CDN_SCRIPT}
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/index.tsx"></script>
  </body>
</html>
`;

/** 使用 .js 配置，避免 Vite 编译 ts 配置时写入 vite.config.ts.timestamp-*.mjs 触发 Nodebox stat 报错 */
const DEFAULT_VITE_CONFIG_JS = `import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(process.cwd(), 'src'),
    },
  },
});
`;

function ensureIndexHtmlWithTailwind(code: string): string {
  if (code.includes("cdn.tailwindcss.com")) return code;
  const snippet = `    ${TAILWIND_CDN_SCRIPT}\n`;
  if (code.includes("</head>")) {
    return code.replace("</head>", `${snippet}  </head>`);
  }
  return DEFAULT_VITE_INDEX_HTML;
}

function applySandpackViteJsConfig(merged: Record<string, { code: string }>) {
  delete merged["/vite.config.ts"];
  for (const key of Object.keys(merged)) {
    if (/^\/vite\.config\.ts\.timestamp-.*\.mjs$/.test(key)) {
      delete merged[key];
    }
  }
  const existing = merged["/vite.config.js"]?.code ?? "";
  if (
    !existing ||
    existing.includes("plugin-react-swc") ||
    existing.includes("timestamp-")
  ) {
    merged["/vite.config.js"] = { code: DEFAULT_VITE_CONFIG_JS };
  }
}

/** 生成文件根目录 → /src 镜像路径，兼容生成代码里的 @/ 别名 */
const ROOT_TO_SRC_MIRROR: Array<[string, string]> = [
  ["/App.tsx", "/src/App.tsx"],
  ["/index.tsx", "/src/index.tsx"],
  ["/styles.css", "/src/styles.css"],
];

/** 保持在项目根目录、不镜像到 /src/ 的文件 */
const SANDPACK_ROOT_ONLY = new Set([
  "/package.json",
  "/package-lock.json",
  "/tsconfig.json",
  "/vite.config.js",
  "/tailwind.config.js",
  "/tailwind.config.ts",
  "/postcss.config.js",
]);

function shouldMirrorGeneratedPathToSrc(path: string): boolean {
  if (path.startsWith("/src/")) return false;
  if (SANDPACK_ROOT_ONLY.has(path)) return false;
  if (path.startsWith("/public/")) return false;
  if (ROOT_TO_SRC_MIRROR.some(([root]) => root === path)) return false;
  return true;
}

function mirrorPathToSrc(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `/src${normalized}`;
}

function isCodePath(path: string): boolean {
  return /\.(ts|tsx|js|jsx)$/.test(path);
}

function dirname(path: string): string {
  const index = path.lastIndexOf("/");
  return index <= 0 ? "/" : path.slice(0, index);
}

function toRelativeImport(fromFile: string, aliasPath: string): string {
  const fromDir = dirname(fromFile).split("/").filter(Boolean);
  const target = `/src/${aliasPath}`.split("/").filter(Boolean);

  while (fromDir.length > 0 && target.length > 0 && fromDir[0] === target[0]) {
    fromDir.shift();
    target.shift();
  }

  const parts = [...fromDir.map(() => ".."), ...target];
  const relative = parts.join("/") || ".";
  return relative.startsWith(".") ? relative : `./${relative}`;
}

function rewriteAliasImportsForSandpack(path: string, code: string): string {
  if (!isCodePath(path)) return code;

  return code.replace(/(["'])(@\/([^"']+)|lucide-react|react-router-dom|sonner)\1/g, (
    match,
    quote: string,
    source: string,
    aliasPath: string | undefined,
  ) => {
    const shimAliasPath =
      source === "lucide-react"
        ? "lib/icons"
        : source === "react-router-dom"
          ? "lib/router"
          : source === "sonner"
            ? "lib/sonner"
            : aliasPath;

    if (!shimAliasPath || (source !== `@/${shimAliasPath}` && !LOCAL_SHIMMED_PACKAGES.has(source))) {
      return match;
    }

    const relativePath = toRelativeImport(path, shimAliasPath);
    return `${quote}${relativePath}${quote}`;
  });
}

function prepareFileForSandpack(path: string, file: { code: string }) {
  const code = rewriteAliasImportsForSandpack(path, file.code);

  return {
    ...file,
    code,
  };
}

function extractLucideIconNames(files: SandpackFiles | null): string[] {
  if (!files) return [];
  const names = new Set<string>();
  const pattern =
    /import\s+\{([^}]+)\}\s+from\s+["'](?:lucide-react|@\/lib\/icons)["']/g;

  for (const [path, file] of Object.entries(files)) {
    if (!isCodePath(path)) continue;
    for (const match of file.code.matchAll(pattern)) {
      for (const item of match[1].split(",")) {
        const imported = item.trim().split(/\s+as\s+/, 1)[0]?.trim();
        if (imported && /^[A-Za-z_$][\w$]*$/.test(imported)) {
          names.add(imported);
        }
      }
    }
  }

  return [...names].sort();
}

function createIconsFallback(files: SandpackFiles | null): { code: string } {
  const exportsCode = extractLucideIconNames(files)
    .map((name) => `export const ${name} = createIcon('${name}');`)
    .join("\n");

  return {
    code: `import React from 'react';

type IconProps = React.SVGProps<SVGSVGElement> & { size?: number | string };

function createIcon(label: string) {
  const Icon = React.forwardRef<SVGSVGElement, IconProps>(
    ({ size = 24, className = '', children, ...props }, ref) => (
      <svg
        ref={ref}
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
        aria-label={props['aria-label'] ?? label}
        {...props}
      >
        {children ?? (
          <>
            <circle cx="12" cy="12" r="9" />
            <path d="M8 12h8" />
            <path d="M12 8v8" />
          </>
        )}
      </svg>
    ),
  );
  Icon.displayName = label;
  return Icon;
}

${exportsCode}
export default createIcon('Icon');
`,
  };
}

function createRouterFallback(): { code: string } {
  return {
    code: `import React from 'react';

type RouteObject = {
  path?: string;
  index?: boolean;
  element?: React.ReactNode;
  children?: RouteObject[];
};

type RouteProps = RouteObject;

type OutletContextValue = {
  outlet: React.ReactNode;
  markUsed: () => void;
};

const OutletContext = React.createContext<OutletContextValue | null>(null);

function currentPath() {
  if (typeof window === 'undefined') return '/';
  const hash = window.location.hash.replace(/^#/, '');
  if (hash.startsWith('/')) return hash;
  const path = window.location.pathname || '/';
  return path.length > 1 ? path : '/';
}

function pathSegments(pathname: string) {
  return pathname.split('/').filter(Boolean);
}

function routeChildren(children: React.ReactNode): React.ReactElement<RouteProps>[] {
  return React.Children.toArray(children).filter(React.isValidElement) as React.ReactElement<RouteProps>[];
}

function OutletFallback({
  element,
  outlet,
}: {
  element: React.ReactNode;
  outlet: React.ReactNode;
}) {
  const [usedOutlet, setUsedOutlet] = React.useState(false);
  const markUsed = React.useCallback(() => setUsedOutlet(true), []);
  const rendered = React.isValidElement(element)
    ? React.cloneElement(element, undefined, outlet)
    : element;

  return (
    <OutletContext.Provider value={{ outlet, markUsed }}>
      {rendered}
      {!usedOutlet ? outlet : null}
    </OutletContext.Provider>
  );
}

function renderWithOutlet(element: React.ReactNode, outlet: React.ReactNode) {
  if (!element) return outlet;
  return <OutletFallback element={element} outlet={outlet} />;
}

function matchRoute(
  route: React.ReactElement<RouteProps>,
  segments: string[],
): React.ReactNode | undefined {
  const { path, index, element, children } = route.props;

  if (index) {
    return segments.length === 0 ? element : undefined;
  }

  if (path === '*') {
    return element;
  }

  let remaining = segments;
  if (path && path !== '/') {
    const routeSegments = pathSegments(path);
    const matched = routeSegments.every(
      (segment, index) => segment.startsWith(':') || segment === segments[index],
    );
    if (!matched) return undefined;
    remaining = segments.slice(routeSegments.length);
  }

  const childRoutes = routeChildren(children);
  const childMatch = matchRoutes(childRoutes, remaining);

  if (childMatch !== undefined) {
    return renderWithOutlet(element, childMatch);
  }

  return remaining.length === 0 ? element : undefined;
}

function matchRoutes(routes: React.ReactElement<RouteProps>[], segments: string[]) {
  for (const route of routes) {
    const match = matchRoute(route, segments);
    if (match !== undefined) return match;
  }
  return undefined;
}

export function BrowserRouter({ children }: { children?: React.ReactNode }) {
  return <>{children}</>;
}

export const HashRouter = BrowserRouter;
export const MemoryRouter = BrowserRouter;

export function Routes({ children }: { children?: React.ReactNode }) {
  const routes = routeChildren(children);
  return <>{matchRoutes(routes, pathSegments(currentPath())) ?? null}</>;
}

export function Route(_props: RouteProps) {
  return null;
}

export function Outlet() {
  const value = React.useContext(OutletContext);
  React.useEffect(() => {
    value?.markUsed();
  }, [value]);
  return <>{value?.outlet ?? null}</>;
}

export function Link({ to, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { to: string }) {
  const target = to.startsWith('#') ? to : '#' + (to.startsWith('/') ? to : '/' + to);
  return <a href={target} {...props}>{children}</a>;
}

export const NavLink = Link;

export function Navigate({ to }: { to: string }) {
  React.useEffect(() => {
    const target = to.startsWith('#') ? to : '#' + (to.startsWith('/') ? to : '/' + to);
    window.location.hash = target.replace(/^#/, '');
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, [to]);
  return null;
}

export function useNavigate() {
  return React.useCallback((to: string | number) => {
    if (typeof to === 'number') {
      window.history.go(to);
      return;
    }
    const target = to.startsWith('#') ? to : '#' + (to.startsWith('/') ? to : '/' + to);
    window.location.hash = target.replace(/^#/, '');
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, []);
}

export function useLocation() {
  const [path, setPath] = React.useState(currentPath());
  React.useEffect(() => {
    const update = () => setPath(currentPath());
    window.addEventListener('popstate', update);
    return () => window.removeEventListener('popstate', update);
  }, []);
  return { pathname: path, search: window.location.search, hash: window.location.hash, state: null, key: 'default' };
}

export function useParams() {
  return {};
}

export function createBrowserRouter(routes: RouteObject[]) {
  return routes;
}

function matchRouteObject(route: RouteObject, segments: string[]): React.ReactNode | undefined {
  if (route.index) return segments.length === 0 ? route.element : undefined;
  if (route.path === '*') return route.element;

  let remaining = segments;
  if (route.path && route.path !== '/') {
    const routeSegments = pathSegments(route.path);
    const matched = routeSegments.every(
      (segment, index) => segment.startsWith(':') || segment === segments[index],
    );
    if (!matched) return undefined;
    remaining = segments.slice(routeSegments.length);
  }

  for (const child of route.children ?? []) {
    const childMatch = matchRouteObject(child, remaining);
    if (childMatch !== undefined) {
      return renderWithOutlet(route.element, childMatch);
    }
  }

  return remaining.length === 0 ? route.element : undefined;
}

export function RouterProvider({ router }: { router: RouteObject[] }) {
  for (const route of router) {
    const match = matchRouteObject(route, pathSegments(currentPath()));
    if (match !== undefined) return <>{match}</>;
  }
  return null;
}
`,
  };
}

function createSonnerFallback(): { code: string } {
  return {
    code: `export function Toaster() {
  return null;
}

export const toast = Object.assign(
  (message: string) => console.log('[toast]', message),
  {
    success: (message: string) => console.log('[toast:success]', message),
    error: (message: string) => console.error('[toast:error]', message),
    info: (message: string) => console.info('[toast:info]', message),
    warning: (message: string) => console.warn('[toast:warning]', message),
  },
);
`,
  };
}

function addPreviewFallbackFiles(
  merged: Record<string, { code: string }>,
  generatedFiles: SandpackFiles | null,
) {
  if (!merged["/lib/icons.tsx"] && !merged["/src/lib/icons.tsx"]) {
    merged["/src/lib/icons.tsx"] = createIconsFallback(generatedFiles);
  }
  if (!merged["/lib/router.tsx"] && !merged["/src/lib/router.tsx"]) {
    merged["/src/lib/router.tsx"] = createRouterFallback();
  }
  if (!merged["/lib/sonner.tsx"] && !merged["/src/lib/sonner.tsx"]) {
    merged["/src/lib/sonner.tsx"] = createSonnerFallback();
  }
}

/**
 * 合并模板与生成文件，并额外镜像到 /src/ 下。
 * Sandpack react-ts 的真实入口是根目录 /index.tsx + /App.tsx；/src 镜像只用于兼容 @/ 别名。
 */
export function mergeSandpackFiles(
  templateFiles: Record<string, { code: string }>,
  generatedFiles: SandpackFiles | null,
): Record<string, { code: string }> {
  const merged: Record<string, { code: string }> = { ...templateFiles };

  if (generatedFiles) {
    Object.entries(generatedFiles).forEach(([path, file]) => {
      if (path === "/package.json") return;
      merged[path] = file;
    });
  }

  const hasGeneratedApp =
    generatedFiles !== null && Object.keys(generatedFiles).length > 0;

  if (hasGeneratedApp) {
    addPreviewFallbackFiles(merged, generatedFiles);

    if (!merged["/index.html"]) {
      merged["/index.html"] = { code: DEFAULT_VITE_INDEX_HTML };
    }

    if (!merged["/index.tsx"]?.code?.includes("createRoot")) {
      merged["/index.tsx"] = {
        code: `import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

const rootEl = document.getElementById('root');
if (rootEl) {
  createRoot(rootEl).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}
`,
      };
    }

    for (const [rootPath, srcPath] of ROOT_TO_SRC_MIRROR) {
      const file = generatedFiles?.[rootPath] ?? merged[rootPath];
      if (file) {
        merged[srcPath] = file;
      }
    }

    for (const path of Object.keys(generatedFiles!)) {
      if (!shouldMirrorGeneratedPathToSrc(path)) continue;
      const file = generatedFiles![path] ?? merged[path];
      if (!file) continue;
      const srcPath = mirrorPathToSrc(path);
      merged[srcPath] = file;
    }

    merged["/src/lib/router.tsx"] = createRouterFallback();

    for (const [path, file] of Object.entries(merged)) {
      if (path === "/package.json" || !isCodePath(path)) continue;
      merged[path] = prepareFileForSandpack(path, file);
    }

    if (merged["/index.html"]) {
      merged["/index.html"] = {
        code: ensureIndexHtmlWithTailwind(merged["/index.html"].code),
      };
    }
  }

  // 模板与生成产物均可能带 Vite 6；Nodebox 生产环境只认 Vite 4 + esbuild-wasm
  const generatedPkg = generatedFiles?.["/package.json"]?.code;
  merged["/package.json"] = {
    code: patchPackageJsonForSandpack(generatedPkg ?? merged["/package.json"]?.code),
  };
  applySandpackViteJsConfig(merged);
  for (const key of Object.keys(merged)) {
    if (/^\/vite\.config\.ts\.timestamp-.*\.mjs$/.test(key)) {
      delete merged[key];
    }
  }

  return merged;
}

export function hasGeneratedApp(files: SandpackFiles | null): boolean {
  return files !== null && Object.keys(files).length > 0;
}

export function getSandpackActiveFile(files: SandpackFiles | null): string {
  if (!hasGeneratedApp(files)) return "/App.tsx";
  return files?.["/App.tsx"] ? "/App.tsx" : "/src/App.tsx";
}

export function getSandpackVisibleFiles(files: SandpackFiles | null): string[] {
  if (hasGeneratedApp(files)) {
    return ["/index.html", "/index.tsx", "/App.tsx", "/styles.css", "/vite.config.js"];
  }
  return ["/index.html", "/App.tsx", "/index.tsx", "/styles.css"];
}

/**
 * 同步所有合并后的文件。根目录文件是 Sandpack react-ts 真正执行的入口；
 * /src 镜像用于支持 @/ 别名和用户在代码视图中查看 src 结构。
 */
export function listSandpackSyncEntries(
  merged: Record<string, { code: string }>,
): Array<[string, string]> {
  return Object.entries(merged).map(([path, file]) => [path, file.code]);
}
