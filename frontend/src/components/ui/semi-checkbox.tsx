/**
 * Semi Checkbox Component
 * 
 * Wraps @douyinfe/semi-ui/Checkbox with backward-compatible API
 */

import * as React from "react"
import { Checkbox as SemiCheckbox } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface CheckboxProps {
  checked?: boolean
  defaultChecked?: boolean
  indeterminate?: boolean
  disabled?: boolean
  onChange?: (checked: boolean, e: Event) => void
  value?: string
  className?: string
  style?: React.CSSProperties
  children?: React.ReactNode
  id?: string
  name?: string
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ 
    checked, 
    defaultChecked, 
    indeterminate,
    disabled, 
    onChange, 
    value, 
    className, 
    style,
    children,
    id,
    name,
    ...props 
  }, ref) => {
    return (
      <SemiCheckbox
        ref={ref}
        checked={checked}
        defaultChecked={defaultChecked}
        indeterminate={indeterminate}
        disabled={disabled}
        onChange={onChange}
        value={value}
        className={cn("semi-checkbox", className)}
        style={style}
        id={id}
        name={name}
        {...props}
      >
        {children}
      </SemiCheckbox>
    )
  }
)

Checkbox.displayName = "Checkbox"

export interface CheckboxGroupProps {
  value?: string[]
  defaultValue?: string[]
  options?: Array<{ label: React.ReactNode; value: string; disabled?: boolean }>
  onChange?: (value: string[]) => void
  disabled?: boolean
  className?: string
  direction?: 'horizontal' | 'vertical'
}

export const CheckboxGroup: React.FC<CheckboxGroupProps> = ({
  value,
  defaultValue,
  options,
  onChange,
  disabled,
  className,
  direction = 'horizontal',
  ...props
}) => {
  return (
    <SemiCheckbox.Group
      value={value}
      defaultValue={defaultValue}
      onChange={onChange}
      disabled={disabled}
      className={cn("semi-checkbox-group", className)}
      {...props}
    >
      {options?.map(opt => (
        <Checkbox 
          key={opt.value} 
          value={opt.value}
          disabled={opt.disabled}
        >
          {opt.label}
        </Checkbox>
      ))}
    </SemiCheckbox.Group>
  )
}

CheckboxGroup.displayName = "CheckboxGroup"
