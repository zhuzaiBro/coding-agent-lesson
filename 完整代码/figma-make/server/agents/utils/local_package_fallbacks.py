"""常见前端包的本地预览兜底。

当 Sandpack iframe 无法从 jsDelivr/unpkg 拉取 npm 包时，注入本地替代实现以保持预览可用。
"""
import re
from typing import Dict, Set


IMPORT_RE = re.compile(
    r"""(?P<prefix>from\s+|import\s+)(?P<quote>['"])(?P<package>lucide-react|react-router-dom|sonner)(?P=quote)"""
)
LUCIDE_IMPORT_RE = re.compile(r"""import\s+\{(?P<imports>[^}]+)\}\s+from\s+['"]@/lib/icons['"]""")


def _rewrite_imports(files: Dict[str, str]) -> Set[str]:
    packages: Set[str] = set()

    for path, code in list(files.items()):
        if not path.endswith((".ts", ".tsx", ".js", ".jsx")):
            continue

        def replace(match: re.Match) -> str:
            package_name = match.group("package")
            packages.add(package_name)
            replacement = {
                "lucide-react": "@/lib/icons",
                "react-router-dom": "@/lib/router",
                "sonner": "@/lib/sonner",
            }[package_name]
            return f"{match.group('prefix')}{match.group('quote')}{replacement}{match.group('quote')}"

        files[path] = IMPORT_RE.sub(replace, code)

    return packages


def _extract_lucide_icon_names(files: Dict[str, str]) -> Set[str]:
    names: Set[str] = set()
    for path, code in files.items():
        if not path.endswith((".ts", ".tsx", ".js", ".jsx")):
            continue
        for match in LUCIDE_IMPORT_RE.finditer(code):
            for item in match.group("imports").split(","):
                raw = item.strip()
                if not raw:
                    continue
                imported = raw.split(" as ", 1)[0].strip()
                if re.match(r"^[A-Za-z_$][\w$]*$", imported):
                    names.add(imported)
    return names


def _icons_file(icon_names: Set[str]) -> str:
    exports = []
    for name in sorted(icon_names):
        exports.append(f"export const {name} = createIcon('{name}');")

    exports_code = "\n".join(exports)
    return f"""import React from 'react';

type IconProps = React.SVGProps<SVGSVGElement> & {{
  size?: number | string;
  absoluteStrokeWidth?: boolean;
}};

function createIcon(label: string) {{
  const Icon = React.forwardRef<SVGSVGElement, IconProps>(
    ({{ size = 24, className = '', children, ...props }}, ref) => (
      <svg
        ref={{ref}}
        width={{size}}
        height={{size}}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={{2}}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={{className}}
        aria-label={{props['aria-label'] ?? label}}
        {{...props}}
      >
        {{children ?? (
          <>
            <circle cx="12" cy="12" r="9" />
            <path d="M8 12h8" />
            <path d="M12 8v8" />
          </>
        )}}
      </svg>
    ),
  );
  Icon.displayName = label;
  return Icon;
}}

{exports_code}
export default createIcon('Icon');
"""


def _router_file() -> str:
    return """import React from 'react';

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
  return typeof window === 'undefined' ? '/' : window.location.pathname || '/';
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
  return <a href={to} {...props}>{children}</a>;
}

export const NavLink = Link;

export function Navigate({ to }: { to: string }) {
  React.useEffect(() => {
    window.history.pushState({}, '', to);
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
    window.history.pushState({}, '', to);
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
"""


def _sonner_file() -> str:
    return """import React from 'react';

export function Toaster() {
  return null;
}

export const toast = Object.assign(
  (message: string) => {
    console.log('[toast]', message);
  },
  {
    success: (message: string) => console.log('[toast:success]', message),
    error: (message: string) => console.error('[toast:error]', message),
    info: (message: string) => console.info('[toast:info]', message),
    warning: (message: string) => console.warn('[toast:warning]', message),
  },
);
"""


def add_local_package_fallbacks(files: Dict[str, str]) -> Dict[str, int]:
    """将常见包 import 重写为本地路径，并注入对应兜底文件。"""
    packages = _rewrite_imports(files)
    added = 0

    if "lucide-react" in packages:
      icon_names = _extract_lucide_icon_names(files)
      files["/lib/icons.tsx"] = _icons_file(icon_names)
      added += 1

    if "react-router-dom" in packages:
      files["/lib/router.tsx"] = _router_file()
      added += 1

    if "sonner" in packages:
      files["/lib/sonner.tsx"] = _sonner_file()
      added += 1

    return {"packageFallbacksAdded": added, "packageImportsRewritten": len(packages)}
