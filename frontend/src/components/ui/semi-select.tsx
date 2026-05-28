/**
 * Semi Select Component
 * 
 * Wraps @douyinfe/semi-ui/Select with enhanced features and styling.
 */

import * as React from "react"
import { Select as SemiSelect } from "@douyinfe/semi-ui"
type SemiSelectProps = any;
import { cn } from "@/lib/utils"

export interface SelectOption {
  label: string
  value: any
  disabled?: boolean
  extra?: Record<string, any>
}

export interface SelectProps extends Omit<SemiSelectProps, 'optionList'> {
  options?: SelectOption[]
  className?: string
  placeholder?: string
}

const Select = React.forwardRef<any, SelectProps>(
  ({ className, options, placeholder, style, ...props }, ref) => {
    const optionList = options?.map(opt => ({
      label: opt.label,
      value: opt.value,
      disabled: opt.disabled,
      ...opt.extra,
    })) || []

    return (
      <SemiSelect
        ref={ref}
        className={cn("semi-select", className)}
        optionList={optionList}
        placeholder={placeholder || "Select..."}
        style={{
          width: '100%',
          borderRadius: 'var(--radius)',
          ...style,
        }}
        {...props}
      />
    )
  }
)
Select.displayName = "Select"

export { Select }