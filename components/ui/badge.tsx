import * as React from "react"
import { cn } from "@/lib/utils"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline';
}

const badgeVariants: Record<string, string> = {
  default: "border-transparent bg-brand-blue text-white shadow",
  secondary: "border-transparent bg-surface-soft text-ink",
  destructive: "border-transparent bg-red-500 text-white shadow",
  outline: "border-border-soft text-ink",
};

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        badgeVariants[variant],
        className
      )}
      {...props}
    />
  )
}

export { Badge }
