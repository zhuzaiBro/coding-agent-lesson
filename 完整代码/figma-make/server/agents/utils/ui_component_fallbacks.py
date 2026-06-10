"""为常见本地 shadcn/ui import 提供确定性兜底文件。"""
import re
from pathlib import Path
from typing import Dict, Optional, Set


UI_IMPORT_RE = re.compile(r"""from\s+['"]@/components/ui/([^'"]+)['"]""")
RELATIVE_UI_IMPORT_RE = re.compile(r"""from\s+['"]\./([^'"]+)['"]""")
SHADCN_UI_TEMPLATE_DIR = Path("templates") / "shadcn-ui" / "components" / "ui"
LIB_UTILS_RE = re.compile(r"""from\s+['"]@/lib/utils['"]""")


def _normalize_path(path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return normalized.replace("\\", "/")


def _path_exists(files: Dict[str, str], path: str) -> bool:
    normalized = _normalize_path(path)
    candidates = {
        normalized,
        f"/src{normalized}",
    }
    if normalized.startswith("/src/"):
        candidates.add(normalized[4:])

    for candidate in candidates:
        if candidate in files:
            return True
        if candidate.endswith((".ts", ".tsx", ".js", ".jsx")):
            continue
        for suffix in (".tsx", ".ts", ".jsx", ".js"):
            if f"{candidate}{suffix}" in files:
                return True
    return False


def _normalize_module_name(raw: str) -> str:
    name = (raw or "").strip()
    for suffix in (".tsx", ".ts", ".jsx", ".js"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _scan_ui_imports(files: Dict[str, str]) -> Set[str]:
    imports: Set[str] = set()
    for path, code in files.items():
        if path.endswith((".ts", ".tsx", ".js", ".jsx")):
            imports.update(
                _normalize_module_name(match)
                for match in UI_IMPORT_RE.findall(code or "")
            )
    return imports


def _rewrite_template_imports(content: str) -> str:
    return re.sub(
        r"""from\s+['"]\.\./\.\./lib/utils['"]""",
        'from "@/lib/utils"',
        content,
    )


def _load_shadcn_template(module_name: str) -> Optional[str]:
    path = Path.cwd() / SHADCN_UI_TEMPLATE_DIR / f"{module_name}.tsx"
    if not path.is_file():
        return None
    return _rewrite_template_imports(path.read_text(encoding="utf-8"))


def _collect_relative_ui_deps(content: str) -> Set[str]:
    return {
        _normalize_module_name(match)
        for match in RELATIVE_UI_IMPORT_RE.findall(content or "")
    }


def _needs_lib_utils(files: Dict[str, str]) -> bool:
    return any(
        path.endswith((".ts", ".tsx", ".js", ".jsx")) and LIB_UTILS_RE.search(code or "")
        for path, code in files.items()
    )


def _lib_utils() -> str:
    return """export function cn(...inputs: Array<string | false | null | undefined>) {
  return inputs.filter(Boolean).join(" ");
}
"""


def _skeleton() -> str:
    return """import React from 'react';
import { cn } from '@/lib/utils';

export function Skeleton({ className = '', ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('animate-pulse rounded-md bg-gray-200', className)} {...props} />;
}
"""


def _button() -> str:
    return """import React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive' | 'secondary' | string;
  size?: 'default' | 'sm' | 'lg' | 'icon' | string;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'default', size = 'default', ...props }, ref) => {
    const variantClass = variant === 'outline'
      ? 'border border-gray-300 bg-white text-gray-900 hover:bg-gray-50'
      : variant === 'ghost'
        ? 'bg-transparent text-gray-900 hover:bg-gray-100'
        : variant === 'destructive'
          ? 'bg-red-600 text-white hover:bg-red-700'
          : 'bg-gray-900 text-white hover:bg-gray-800';
    const sizeClass = size === 'sm' ? 'h-8 px-3 text-sm' : size === 'lg' ? 'h-11 px-6' : size === 'icon' ? 'h-10 w-10' : 'h-10 px-4';
    return <button ref={ref} className={cn('inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:pointer-events-none disabled:opacity-50', variantClass, sizeClass, className)} {...props} />;
  }
);
Button.displayName = 'Button';
"""


def _card() -> str:
    return """import React from 'react';
import { cn } from '@/lib/utils';

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className = '', ...props }, ref) => <div ref={ref} className={cn('rounded-lg border border-gray-200 bg-white text-gray-950 shadow-sm', className)} {...props} />);
export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className = '', ...props }, ref) => <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />);
export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(({ className = '', ...props }, ref) => <h3 ref={ref} className={cn('text-2xl font-semibold leading-none tracking-normal', className)} {...props} />);
export const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(({ className = '', ...props }, ref) => <p ref={ref} className={cn('text-sm text-gray-500', className)} {...props} />);
export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className = '', ...props }, ref) => <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />);
export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className = '', ...props }, ref) => <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />);
Card.displayName = 'Card';
CardHeader.displayName = 'CardHeader';
CardTitle.displayName = 'CardTitle';
CardDescription.displayName = 'CardDescription';
CardContent.displayName = 'CardContent';
CardFooter.displayName = 'CardFooter';
"""


def _form_control(tag: str, name: str, base: str) -> str:
    return f"""import React from 'react';
import {{ cn }} from '@/lib/utils';

export const {name} = React.forwardRef<React.ElementRef<'{tag}'>, React.ComponentPropsWithoutRef<'{tag}'>>(
  ({{ className = '', ...props }}, ref) => <{tag} ref={{ref}} className={{cn('{base}', className)}} {{...props}} />
);
{name}.displayName = '{name}';
"""


def _badge() -> str:
    return """import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'destructive' | string;
}

export function Badge({ className = '', variant = 'default', ...props }: BadgeProps) {
  const variantClass = variant === 'outline' ? 'border border-gray-300 text-gray-900' : variant === 'destructive' ? 'bg-red-600 text-white' : variant === 'secondary' ? 'bg-gray-100 text-gray-900' : 'bg-gray-900 text-white';
  return <div className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold', variantClass, className)} {...props} />;
}
"""


def _alert() -> str:
    return """import React from 'react';
import { cn } from '@/lib/utils';

export const Alert = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className = '', ...props }, ref) => <div ref={ref} role="alert" className={cn('relative w-full rounded-lg border border-gray-200 p-4', className)} {...props} />);
export const AlertTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(({ className = '', ...props }, ref) => <h5 ref={ref} className={cn('mb-1 font-medium leading-none tracking-normal', className)} {...props} />);
export const AlertDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(({ className = '', ...props }, ref) => <div ref={ref} className={cn('text-sm text-gray-600', className)} {...props} />);
Alert.displayName = 'Alert';
AlertTitle.displayName = 'AlertTitle';
AlertDescription.displayName = 'AlertDescription';
"""


def _checkbox() -> str:
    return """import React from 'react';
import { cn } from '@/lib/utils';

export const Checkbox = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className = '', ...props }, ref) => (
    <input
      type="checkbox"
      ref={ref}
      className={cn('h-4 w-4 rounded border border-gray-300 text-gray-900 focus:ring-gray-400', className)}
      {...props}
    />
  )
);
Checkbox.displayName = 'Checkbox';
"""


def _table() -> str:
    return """import React from 'react';
import { cn } from '@/lib/utils';

export const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(({ className = '', ...props }, ref) => <div className="relative w-full overflow-auto"><table ref={ref} className={cn('w-full caption-bottom text-sm', className)} {...props} /></div>);
export const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(({ className = '', ...props }, ref) => <thead ref={ref} className={cn('[&_tr]:border-b', className)} {...props} />);
export const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(({ className = '', ...props }, ref) => <tbody ref={ref} className={cn('[&_tr:last-child]:border-0', className)} {...props} />);
export const TableFooter = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(({ className = '', ...props }, ref) => <tfoot ref={ref} className={cn('border-t bg-gray-50 font-medium', className)} {...props} />);
export const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(({ className = '', ...props }, ref) => <tr ref={ref} className={cn('border-b transition-colors hover:bg-gray-50', className)} {...props} />);
export const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(({ className = '', ...props }, ref) => <th ref={ref} className={cn('h-12 px-4 text-left align-middle font-medium text-gray-500', className)} {...props} />);
export const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(({ className = '', ...props }, ref) => <td ref={ref} className={cn('p-4 align-middle', className)} {...props} />);
export const TableCaption = React.forwardRef<HTMLTableCaptionElement, React.HTMLAttributes<HTMLTableCaptionElement>>(({ className = '', ...props }, ref) => <caption ref={ref} className={cn('mt-4 text-sm text-gray-500', className)} {...props} />);
"""


FALLBACKS = {
    "alert": _alert,
    "badge": _badge,
    "button": _button,
    "card": _card,
    "checkbox": _checkbox,
    "input": lambda: _form_control("input", "Input", "flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-gray-400 disabled:cursor-not-allowed disabled:opacity-50"),
    "label": lambda: _form_control("label", "Label", "text-sm font-medium leading-none"),
    "skeleton": _skeleton,
    "table": _table,
    "textarea": lambda: _form_control("textarea", "Textarea", "flex min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-gray-400 disabled:cursor-not-allowed disabled:opacity-50"),
}


def add_missing_ui_fallbacks(files: Dict[str, str]) -> Dict[str, int]:
    """为缺失的 shadcn/ui 模块 import 补充本地兜底文件。"""
    added = 0
    unknown = 0

    if _needs_lib_utils(files) and not _path_exists(files, "/lib/utils"):
        files["/lib/utils.ts"] = _lib_utils()
        added += 1

    queue = sorted(_scan_ui_imports(files))
    seen: Set[str] = set()

    while queue:
        module_name = queue.pop(0)
        if module_name in seen:
            continue
        seen.add(module_name)

        target = f"/components/ui/{module_name}"
        if _path_exists(files, target):
            continue

        factory = FALLBACKS.get(module_name)
        if factory:
            content = factory()
        else:
            content = _load_shadcn_template(module_name)

        if not content:
            unknown += 1
            continue

        files[f"{target}.tsx"] = content
        added += 1

        if not _path_exists(files, "/lib/utils"):
            files["/lib/utils.ts"] = _lib_utils()
            added += 1

        for dep in sorted(_collect_relative_ui_deps(content)):
            dep_target = f"/components/ui/{dep}"
            if dep not in seen and not _path_exists(files, dep_target):
                queue.append(dep)

    return {"uiFallbacksAdded": added, "unknownUiImports": unknown}
