/**
 * Semi Badge Component
 * 
 * Wraps @douyinfe/semi-ui/Badge with backward-compatible API
 */

import * as React from "react"
import { Badge as SemiBadge } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface BadgeProps {
  count?: number | React.ReactNode
  dot?: boolean
  showZero?: boolean
  overflowCount?: number
  status?: 'success' | 'warning' | 'error' | 'info' | 'default'
  type?: 'primary' | 'secondary' | 'danger' | 'warning' | 'success'
  className?: string
  style?: React.CSSProperties
  children?: React.ReactNode
  color?: string
  inverted?: boolean
}

export const Badge: React.FC<BadgeProps> = ({
  count,
  dot = false,
  showZero = false,
  overflowCount = 99,
  status,
  type,
  className,
  style,
  children,
  color,
  inverted = false,
  ...props
}) => {
  return (
    <SemiBadge
      count={count}
      dot={dot}
      showZero={showZero}
      overflowCount={overflowCount}
      status={status}
      type={type}
      className={cn("semi-badge", className)}
      style={style}
      color={color}
      inverted={inverted}
      {...props}
    >
      {children}
    </SemiBadge>
  )
}

Badge.displayName = "Badge"

export interface BadgeDotProps {
  status?: 'success' | 'warning' | 'error' | 'info' | 'default'
  className?: string
  style?: React.CSSProperties
}

export const BadgeDot: React.FC<BadgeDotProps> = ({
  status,
  className,
  style,
  ...props
}) => {
  return (
    <SemiBadge.Dot
      status={status}
      className={cn("semi-badge-dot", className)}
      style={style}
      {...props}
    />
  )
}

BadgeDot.displayName = "BadgeDot"
