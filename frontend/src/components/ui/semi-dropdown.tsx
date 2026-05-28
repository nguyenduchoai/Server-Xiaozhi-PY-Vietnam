/**
 * Semi Dropdown Component
 * 
 * Wraps @douyinfe/semi-ui/Dropdown with enhanced styling.
 */

import * as React from "react"
import { Dropdown as SemiDropdown } from "@douyinfe/semi-ui"
import type { DropdownProps as SemiDropdownProps } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface DropdownProps extends Omit<SemiDropdownProps, 'render'> {
  className?: string
  trigger?: 'hover' | 'click' | 'focus'
  menu?: React.ReactNode
  children?: React.ReactNode
}

const Dropdown = React.forwardRef<HTMLDivElement, DropdownProps>(
  ({ className, trigger = 'hover', menu, children, ...props }, ref) => {
    return (
      <SemiDropdown
        ref={ref}
        className={cn("semi-dropdown", className)}
        trigger={trigger}
        render={menu}
        {...props}
      >
        {children}
      </SemiDropdown>
    )
  }
)
Dropdown.displayName = "Dropdown"

export interface DropdownItemProps {
  label?: React.ReactNode
  icon?: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  className?: string
}

const DropdownItem = React.forwardRef<HTMLDivElement, DropdownItemProps>(
  ({ label, icon, onClick, disabled, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex items-center gap-2 px-4 py-2 cursor-pointer hover:bg-accent",
          "text-sm transition-colors",
          disabled && "opacity-50 cursor-not-allowed",
          className
        )}
        onClick={disabled ? undefined : onClick}
        role="menuitem"
        {...props}
      >
        {icon && <span className="flex items-center">{icon}</span>}
        <span>{label}</span>
      </div>
    )
  }
)
DropdownItem.displayName = "DropdownItem"

const DropdownMenu = ({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "bg-background border rounded-md shadow-lg p-1 min-w-[160px]",
      className
    )}
    style={{
      backgroundColor: 'var(--background)',
      borderColor: 'var(--border)',
    }}
    role="menu"
    {...props}
  >
    {children}
  </div>
)
DropdownMenu.displayName = "DropdownMenu"

const DropdownSeparator = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("h-px bg-border my-1", className)}
    style={{ backgroundColor: 'var(--border)' }}
    role="separator"
    {...props}
  />
)
DropdownSeparator.displayName = "DropdownSeparator"

export {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSeparator,
}