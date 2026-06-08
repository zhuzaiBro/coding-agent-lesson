import * as React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline";
}

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        variant === "default" && "border-transparent bg-gray-900 text-white",
        variant === "secondary" &&
          "border-transparent bg-gray-100 text-gray-900",
        variant === "outline" && "border-gray-300 text-gray-700",
        className,
      )}
      {...props}
    />
  );
}
