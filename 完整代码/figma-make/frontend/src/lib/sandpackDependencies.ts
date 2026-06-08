import type { SandpackFiles } from "@/types/store";

export const SANDPACK_BASE_DEPENDENCIES: Record<string, string> = {
  react: "18.2.0",
  "react-dom": "18.2.0",
};

export const LOCAL_SHIMMED_PACKAGES = new Set([
  "lucide-react",
  "react-router-dom",
  "sonner",
]);

type PackageJson = {
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
};

/**
 * Sandpack Nodebox 仅支持 WASM 版 Rollup（linux/x32 无原生包）。
 * 工具链版本与官方 vite-react-ts 模板对齐，勿用生成产物里的 Vite 6。
 */
export const VITE_SANDPACK_DEV_DEPS: Record<string, string> = {
  vite: "4.2.0",
  "@vitejs/plugin-react": "4.3.4",
  "@rollup/wasm-node": "4.61.1",
  typescript: "4.9.5",
  "esbuild-wasm": "0.17.19",
  "@types/react": "18.3.18",
  "@types/react-dom": "18.3.5",
};

/** 生成 package.json 里的 devDeps 不能覆盖 Sandpack 工具链 */
const SANDBOX_TOOLCHAIN_BLOCKLIST = new Set([
  "vite",
  "rollup",
  "esbuild",
  "@rollup/wasm-node",
  "@vitejs/plugin-react",
  "@vitejs/plugin-react-swc",
  "esbuild-wasm",
  "typescript",
]);

function getPackageName(source: string): string {
  if (source.startsWith("@")) {
    const [scope, name] = source.split("/");
    return `${scope}/${name}`;
  }
  return source.split("/")[0];
}

function isBarePackageImport(source: string): boolean {
  return (
    !source.startsWith(".") &&
    !source.startsWith("/") &&
    !source.startsWith("@/")
  );
}

function collectBareImports(files: SandpackFiles | null): Set<string> {
  const imports = new Set<string>();
  if (!files) return imports;

  const importPattern =
    /(?:import|export)\s+(?:[^'"]*?\s+from\s+)?["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)|require\(\s*["']([^"']+)["']\s*\)/g;

  for (const [path, file] of Object.entries(files)) {
    if (!/\.(ts|tsx|js|jsx)$/.test(path)) continue;

    for (const match of file.code.matchAll(importPattern)) {
      const source = match[1] ?? match[2] ?? match[3];
      if (!source || !isBarePackageImport(source)) continue;
      imports.add(getPackageName(source));
    }
  }

  return imports;
}

export function safeParsePackageJson(code: string | undefined): PackageJson {
  if (!code) return {};
  try {
    const parsed = JSON.parse(code) as PackageJson;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

export function getPreviewDependencies(files: SandpackFiles | null) {
  const packageFile = files?.["/package.json"] ?? files?.["/src/package.json"];
  const packageJson = safeParsePackageJson(packageFile?.code);
  const bareImports = collectBareImports(files);

  const fromPackage = Object.fromEntries(
    Object.entries(packageJson.dependencies ?? {}).filter(
      ([name]) => !LOCAL_SHIMMED_PACKAGES.has(name),
    ),
  );

  const fromImports = Object.fromEntries(
    Object.entries(packageJson.dependencies ?? {}).filter(
      ([name]) => bareImports.has(name) && !LOCAL_SHIMMED_PACKAGES.has(name),
    ),
  );

  return {
    ...SANDPACK_BASE_DEPENDENCIES,
    ...fromPackage,
    ...fromImports,
  };
}

export function getAdditionalPreviewDependencies(files: SandpackFiles | null) {
  const dependencies = getPreviewDependencies(files);
  return Object.fromEntries(
    Object.entries(dependencies).filter(
      ([name]) => !(name in SANDPACK_BASE_DEPENDENCIES),
    ),
  );
}

export function getPreviewDevDependencies(files: SandpackFiles | null) {
  const packageFile = files?.["/package.json"] ?? files?.["/src/package.json"];
  const packageJson = safeParsePackageJson(packageFile?.code);
  const fromPackage = Object.fromEntries(
    Object.entries(packageJson.devDependencies ?? {}).filter(
      ([name]) =>
        !SANDBOX_TOOLCHAIN_BLOCKLIST.has(name) &&
        !name.startsWith("@rollup/") &&
        name.startsWith("@types/"),
    ),
  );
  return { ...fromPackage, ...VITE_SANDPACK_DEV_DEPS };
}

/** 写入 Sandpack 的 package.json：强制 Rollup WASM，避免 Nodebox linux/x32 崩溃 */
export function patchPackageJsonForSandpack(code: string | undefined): string {
  const pkg = safeParsePackageJson(code) as Record<string, unknown>;
  const deps = (pkg.dependencies as Record<string, string>) ?? {};
  const devDeps = { ...((pkg.devDependencies as Record<string, string>) ?? {}) };

  for (const key of SANDBOX_TOOLCHAIN_BLOCKLIST) {
    delete devDeps[key];
  }
  for (const key of Object.keys(devDeps)) {
    if (key.startsWith("@rollup/") || key.startsWith("@vitejs/")) {
      delete devDeps[key];
    }
  }

  Object.assign(devDeps, VITE_SANDPACK_DEV_DEPS);

  const next = {
    name: pkg.name ?? "sandpack-preview",
    private: true,
    type: "module",
    scripts: {
      dev: "vite",
      build: "vite build",
      ...(pkg.scripts as Record<string, string>),
    },
    dependencies: deps,
    devDependencies: devDeps,
    overrides: {
      ...((pkg.overrides as Record<string, string>) ?? {}),
      rollup: "npm:@rollup/wasm-node@4.61.1",
      vite: "4.2.0",
      esbuild: "npm:esbuild-wasm@0.17.19",
    },
    pnpm: {
      overrides: {
        ...(((pkg.pnpm as { overrides?: Record<string, string> })?.overrides) ??
          {}),
        vite: "4.2.0",
        esbuild: "npm:esbuild-wasm@0.17.19",
        rollup: "npm:@rollup/wasm-node@4.61.1",
      },
    },
  };

  return JSON.stringify(next, null, 2);
}
