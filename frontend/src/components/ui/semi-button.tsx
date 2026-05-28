import * as React from "react"
import { Button as SemiButton } from "@douyinfe/semi-ui"
import type { ButtonProps as SemiButtonProps } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface ButtonProps extends Omit<SemiButtonProps, 'size' | 'theme' | 'htmlType'> {
  variant?: "primary" | "secondary" | "tertiary" | "warning" | "danger" | "light" | "ghost" | "outline" | "link" | "default"
  size?: "small" | "medium" | "large" | "default" | "icon" | "icon-sm" | "icon-lg"
  asChild?: boolean
}

const VARIANT_CLASSES: Record<string, string> = {
  default: "bg-primary text-primary-foreground hover:bg-primary/90",
  primary: "bg-blue-500 text-white hover:bg-blue-600",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  tertiary: "bg-tertiary text-tertiary-foreground hover:bg-tertiary/80",
  warning: "bg-warning text-warning-foreground hover:bg-warning/90",
  danger: "bg-destructive text-white hover:bg-destructive/90",
  light: "bg-light text-light-foreground hover:bg-light/80",
  ghost: "hover:bg-accent hover:text-accent-foreground",
  outline: "border bg-background shadow-xs hover:bg-accent hover:text-accent-foreground",
  link: "text-primary underline-offset-4 hover:underline",
}

const SIZE_CLASSES: Record<string, string> = {
  default: "h-9 px-4 py-2",
  small: "h-8 rounded-md px-3 text-sm",
  medium: "h-10 px-4",
  large: "h-10 rounded-md px-6",
  icon: "size-9 w-[36px] h-[36px]",
  "icon-sm": "size-8 w-[32px] h-[32px]",
  "icon-lg": "size-10 w-[40px] h-[40px]",
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", disabled, loading, children, ...props }, ref) => {
    const semiTheme = variant === "primary" || variant === "danger" || variant === "warning" 
      ? "solid" 
      : variant === "ghost" || variant === "link" || variant === "outline"
        ? "none"
        : "light"

    const semiSize = size === "default" ? "medium" 
      : size === "icon" || size === "icon-sm" || size === "icon-lg" ? "small" 
      : size as any

    const iconOnly = size === "icon" || size === "icon-sm" || size === "icon-lg"

    return (
      <SemiButton
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all",
          "disabled:pointer-events-none disabled:opacity-50",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          iconOnly && "rounded-full",
          className
        )}
        theme={semiTheme}
        size={semiSize as any}
        disabled={disabled}
        loading={loading}
        {...props}
      >
        {children}
      </SemiButton>
    )
  }
)
Button.displayName = "Button"

export { Button, VARIANT_CLASSES, SIZE_CLASSES }