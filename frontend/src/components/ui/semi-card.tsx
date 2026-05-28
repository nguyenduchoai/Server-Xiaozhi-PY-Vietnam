import * as React from "react"
import { Card as SemiCard } from "@douyinfe/semi-ui"
import type { CardProps as SemiCardProps } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface CardProps extends Omit<SemiCardProps, 'shadow'> {
  shadow?: "none" | "hover" | "active" | "elevation_1" | "elevation_2" | "elevation_3"
}

const SHADOW_CLASSES: Record<string, string> = {
  none: "shadow-none",
  hover: "hover:shadow-md transition-shadow",
  active: "shadow-md",
  elevation_1: "shadow-sm",
  elevation_2: "shadow-md",
  elevation_3: "shadow-lg",
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, style, shadow = "none", ...props }, ref) => {
    return (
      <SemiCard
        ref={ref}
        className={cn(
          "rounded-lg border bg-card text-card-foreground",
          SHADOW_CLASSES[shadow],
          className
        )}
        style={{
          ...style,
          borderRadius: 'var(--radius)',
          backgroundColor: 'var(--card)',
          borderColor: 'var(--border)',
        } as React.CSSProperties}
        shadow={shadow === "none" ? undefined : shadow}
        {...props}
      />
    )
  }
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col space-y-1.5 p-6", className)}
      {...props}
    />
  )
)
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn("text-lg font-semibold leading-none tracking-tight", className)}
      style={{ color: 'var(--foreground)' }}
      {...props}
    />
  )
)
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn("text-sm text-muted-foreground", className)}
      style={{ color: 'var(--muted-foreground)' }}
      {...props}
    />
  )
)
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("p-6 pt-0", className)}
      {...props}
    />
  )
)
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex items-center p-6 pt-0", className)}
      {...props}
    />
  )
)
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter }