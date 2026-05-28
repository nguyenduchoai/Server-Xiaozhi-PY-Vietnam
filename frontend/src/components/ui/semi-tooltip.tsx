/**
 * Semi Tooltip Component
 * 
 * Wraps @douyinfe/semi-ui/Tooltip with backward-compatible API
 */

import * as React from "react"
import { Tooltip as SemiTooltip } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface TooltipProps {
  children?: React.ReactNode
  content?: React.ReactNode
  className?: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  trigger?: 'hover' | 'click' | 'focus'
  showArrow?: boolean
  delay?: number
  spacing?: number
}

export const Tooltip: React.FC<TooltipProps> = ({
  children,
  content,
  className,
  position = 'top',
  trigger = 'hover',
  delay = 200,
  spacing = 4,
  ...props
}) => {
  if (!children) return null

  return (
    <SemiTooltip
      content={content}
      position={position}
      trigger={trigger}
      delay={delay}
      spacing={spacing}
      className={cn("semi-tooltip", className)}
      {...props}
    >
      {children}
    </SemiTooltip>
  )
}

Tooltip.displayName = "Tooltip"
