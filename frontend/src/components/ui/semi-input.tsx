import * as React from "react"
import { Input as SemiInput, TextArea as SemiTextArea } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface InputProps {
  className?: string
  [key: string]: any
}

export interface TextareaProps {
  className?: string
  [key: string]: any
}

const Input = React.forwardRef<any, InputProps>(
  ({ className, style, ...props }, ref) => {
    return (
      <SemiInput
        ref={ref}
        className={cn(
          "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          "placeholder:text-muted-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        style={{
          ...style,
          borderRadius: 'var(--radius)',
        } as React.CSSProperties}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

const Textarea = React.forwardRef<any, TextareaProps>(
  ({ className, style, ...props }, ref) => {
    return (
      <SemiTextArea
        ref={ref}
        className={cn(
          "flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm",
          "placeholder:text-muted-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        style={{
          ...style,
          borderRadius: 'var(--radius)',
        } as React.CSSProperties}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Input, Textarea }