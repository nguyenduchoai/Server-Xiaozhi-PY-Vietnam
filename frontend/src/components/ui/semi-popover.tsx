/**
 * Semi Popover Component
 * 
 * Wraps @douyinfe/semi-ui/Popover with backward-compatible API
 */

import * as React from "react"
import { Popover as SemiPopover } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface PopoverProps {
  children?: React.ReactNode
  content?: React.ReactNode
  title?: React.ReactNode
  className?: string
  position?: 'top' | 'bottom' | 'left' | 'right' | 'topLeft' | 'topRight' | 'bottomLeft' | 'bottomRight' | 'leftTop' | 'leftBottom' | 'rightTop' | 'rightBottom'
  trigger?: 'hover' | 'click' | 'focus' | 'custom'
  visible?: boolean
  onVisibleChange?: (visible: boolean) => void
  showArrow?: boolean
  spacing?: number
}

export const Popover: React.FC<PopoverProps> = ({
  children,
  content,
  title,
  className,
  position = 'bottomLeft',
  trigger = 'click',
  visible,
  onVisibleChange,
  spacing = 8,
  ...props
}) => {
  return (
    <SemiPopover
      content={
        <>
          {title && <div className="font-semibold mb-2">{title}</div>}
          {content}
        </>
      }
      position={position}
      trigger={trigger}
      visible={visible}
      onVisibleChange={onVisibleChange}
      spacing={spacing}
      className={cn("semi-popover", className)}
      {...props}
    >
      {children}
    </SemiPopover>
  )
}

Popover.displayName = "Popover"
