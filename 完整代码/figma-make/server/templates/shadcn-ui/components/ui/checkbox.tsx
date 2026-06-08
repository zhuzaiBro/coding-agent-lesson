import * as React from "react";
import { cn } from "../../lib/utils";

export const Checkbox = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    type="checkbox"
    ref={ref}
    className={cn(
      "h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-400",
      className,
    )}
    {...props}
  />
));
Checkbox.displayName = "Checkbox";
