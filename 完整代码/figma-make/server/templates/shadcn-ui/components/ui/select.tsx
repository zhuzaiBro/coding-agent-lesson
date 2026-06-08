import * as React from "react";
import { cn } from "../../lib/utils";

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "flex h-9 w-full rounded-md border border-gray-300 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 disabled:cursor-not-allowed disabled:opacity-50",
      className,
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";

export const SelectTrigger = Select;
export const SelectValue = ({ children }: { children?: React.ReactNode }) => (
  <>{children}</>
);
export const SelectContent = ({
  children,
}: {
  children?: React.ReactNode;
}) => <>{children}</>;
export const SelectItem = ({
  children,
  value,
  ...props
}: React.OptionHTMLAttributes<HTMLOptionElement>) => (
  <option value={value} {...props}>
    {children}
  </option>
);
