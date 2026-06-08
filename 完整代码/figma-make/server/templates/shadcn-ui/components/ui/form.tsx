import * as React from "react";
import { cn } from "../../lib/utils";
import { Label } from "./label";

export const Form = ({
  children,
  className,
  ...props
}: React.FormHTMLAttributes<HTMLFormElement>) => (
  <form className={cn("space-y-4", className)} {...props}>
    {children}
  </form>
);

export const FormField = ({
  children,
  className,
}: {
  children?: React.ReactNode;
  className?: string;
}) => <div className={cn("space-y-2", className)}>{children}</div>;

export const FormItem = FormField;

export const FormLabel = Label;

export const FormControl = ({
  children,
}: {
  children?: React.ReactNode;
}) => <>{children}</>;

export const FormMessage = ({
  children,
  className,
}: {
  children?: React.ReactNode;
  className?: string;
}) =>
  children ? (
    <p className={cn("text-sm text-red-600", className)}>{children}</p>
  ) : null;
