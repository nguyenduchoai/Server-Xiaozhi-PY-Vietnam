/**
 * Semi Alert Component
 * 
 * Wraps @douyinfe/semi-ui/Banner for consistent alert messaging.
 */

import * as React from "react"
import { Banner as SemiBanner } from "@douyinfe/semi-ui"
import type { BannerProps as SemiBannerProps } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export type AlertVariant = 'info' | 'success' | 'warning' | 'danger' | 'default'

export interface AlertProps extends Omit<SemiBannerProps, 'type'> {
  variant?: AlertVariant
  className?: string
  title?: React.ReactNode
  description?: React.ReactNode
}

const VARIANT_STYLES: Record<AlertVariant, object> = {
  info: {
    backgroundColor: 'rgba(0, 122, 255, 0.1)',
    borderColor: 'rgba(0, 122, 255, 0.2)',
    color: '#007AFF',
  },
  success: {
    backgroundColor: 'rgba(52, 199, 89, 0.1)',
    borderColor: 'rgba(52, 199, 89, 0.2)',
    color: '#34C759',
  },
  warning: {
    backgroundColor: 'rgba(255, 149, 0, 0.1)',
    borderColor: 'rgba(255, 149, 0, 0.2)',
    color: '#FF9500',
  },
  danger: {
    backgroundColor: 'rgba(255, 59, 48, 0.1)',
    borderColor: 'rgba(255, 59, 48, 0.2)',
    color: '#FF3B30',
  },
  default: {
    backgroundColor: 'rgba(142, 142, 147, 0.12)',
    borderColor: 'rgba(142, 142, 147, 0.2)',
    color: '#8E8E93',
  },
}

const VARIANT_SEMI_TYPES: Record<AlertVariant, SemiBannerProps['type']> = {
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  default: 'info',
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ variant = 'default', className, title, description, children, style, ...props }, ref) => {
    const variantStyle = VARIANT_STYLES[variant]
    const semiType = VARIANT_SEMI_TYPES[variant]

    return (
      <SemiBanner
        ref={ref}
        type={semiType}
        className={cn("semi-alert", className)}
        style={{
          borderRadius: 'var(--radius)',
          ...variantStyle,
          ...style,
        }}
        {...props}
      >
        {title && <strong>{title}</strong>}
        {description && <p>{description}</p>}
        {children}
      </SemiBanner>
    )
  }
)
Alert.displayName = "Alert"

export { Alert }