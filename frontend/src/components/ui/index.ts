/**
 * Semi UI Component Index
 * 
 * This file provides backward-compatible exports for the shadcn/ui component API
 * while using @douyinfe/semi-ui as the underlying implementation.
 * 
 * Migration Status (Updated 2026-04-14):
 * ✅ Completed:
 * - semi-button.tsx
 * - semi-input.tsx (Input + Textarea)
 * - semi-card.tsx (Card + CardHeader + CardTitle + etc.)
 * - semi-dialog.tsx (Dialog + DialogTrigger + etc.)
 * - semi-select.tsx
 * - semi-tabs.tsx (Tabs + TabPane)
 * - semi-table.tsx (Table + Column)
 * - semi-dropdown.tsx (Dropdown + DropdownMenu + etc.)
 * - semi-alert.tsx
 * - semi-pagination.tsx
 */

// ============================================================================
// BUTTON COMPONENTS
// ============================================================================
export { Button } from './semi-button'
export type { ButtonProps } from './semi-button'

// ============================================================================
// INPUT COMPONENTS
// ============================================================================
export { Input, Textarea } from './semi-input'
export type { InputProps, TextareaProps } from './semi-input'

// ============================================================================
// CARD COMPONENTS
// ============================================================================
export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './semi-card'
export type { CardProps } from './semi-card'

// ============================================================================
// DIALOG COMPONENTS
// ============================================================================
export {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from './semi-dialog'
export type { DialogProps, DialogTriggerProps } from './semi-dialog'


// ============================================================================
// SELECT COMPONENT (Semi UI wrapper)
// ============================================================================
export { Select } from './semi-select'
export type { SelectProps, SelectOption } from './semi-select'

// ============================================================================
// TABS COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Tabs, TabPane } from './semi-tabs'
export type { TabsProps, TabPaneProps } from './semi-tabs'

// ============================================================================
// TABLE COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Table, Column } from './semi-table'
export type { TableProps, ColumnProps } from './semi-table'

// ============================================================================
// DROPDOWN COMPONENTS (Semi UI wrappers)
// ============================================================================
export {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSeparator,
} from './semi-dropdown'
export type { DropdownProps, DropdownItemProps } from './semi-dropdown'

// ============================================================================
// ALERT COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Alert } from './semi-alert'
export type { AlertProps, AlertVariant } from './semi-alert'

// ============================================================================
// PAGINATION COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Pagination } from './semi-pagination'
export type { PaginationProps } from './semi-pagination'

// ============================================================================
// TOOLTIP COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Tooltip } from './semi-tooltip'
export type { TooltipProps } from './semi-tooltip'

// ============================================================================
// POPOVER COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Popover } from './semi-popover'
export type { PopoverProps } from './semi-popover'

// ============================================================================
// CHECKBOX COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Checkbox, CheckboxGroup } from './semi-checkbox'
export type { CheckboxProps, CheckboxGroupProps } from './semi-checkbox'

// ============================================================================
// AVATAR COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Avatar, AvatarGroup } from './semi-avatar'
export type { AvatarProps, AvatarGroupProps } from './semi-avatar'

// ============================================================================
// BADGE COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Badge, BadgeDot } from './semi-badge'
export type { BadgeProps, BadgeDotProps } from './semi-badge'

// ============================================================================
// SKELETON COMPONENTS (Semi UI wrappers)
// ============================================================================
export { Skeleton, SkeletonParagraph, SkeletonTitle, SkeletonAvatar, SkeletonImage } from './semi-skeleton'
export type { SkeletonProps, SkeletonParagraphProps, SkeletonTitleProps, SkeletonAvatarProps, SkeletonImageProps } from './semi-skeleton'

// ============================================================================
// RE-EXPORTS FROM SHADCN (legacy - for backward compatibility)
// ============================================================================

export { Label } from './label'
export { Switch } from './switch'
export { Progress } from './progress'
export { Separator } from './separator'
export { ScrollArea } from './scroll-area'
export { Breadcrumb } from './breadcrumb'
export { RadioGroup } from './radio-group'
export { Spinner } from './spinner'
export { Empty } from './empty'
export { Sheet } from './sheet'
export { Sidebar } from './sidebar'
export { Collapsible } from './collapsible'
export { AlertDialog } from './alert-dialog'
export { Command } from './command'
export { Combobox } from './combobox'

// ============================================================================
// FEATURE FLAGS
// ============================================================================

export const FEATURE_FLAGS = {
  USE_SEMI_WRAPPERS: true,
  SEMI_MIGRATION_COMPLETE: true,
  SEMI_FORM_ENABLED: true,
  SEMI_SELECT_ENABLED: true,
  SEMI_TABLE_ENABLED: true,
  SEMI_TABS_ENABLED: true,
  SEMI_DROPDOWN_ENABLED: true,
} as const

export type FeatureKey = keyof typeof FEATURE_FLAGS

export function isFeatureEnabled(feature: FeatureKey): boolean {
  return FEATURE_FLAGS[feature]
}

// ============================================================================
// MIGRATION STATUS
// ============================================================================

export const COMPONENT_MIGRATION_STATUS = {
  total: 21,
  completed: 18,
  pending: 3,
  percentage: 86,
} as const

// ============================================================================
// COMPONENT MIGRATION MAP
// ============================================================================

export const COMPONENT_MIGRATION_MAP = {
  'Button': {
    status: 'completed',
    file: 'semi-button.tsx',
    semiComponent: '@douyinfe/semi-ui/Button',
    priority: 'high',
    tested: true,
  },
  'Input': {
    status: 'completed',
    file: 'semi-input.tsx',
    semiComponent: '@douyinfe/semi-ui/Input',
    priority: 'high',
    tested: true,
  },
  'Textarea': {
    status: 'completed',
    file: 'semi-input.tsx',
    semiComponent: '@douyinfe/semi-ui/TextArea',
    priority: 'high',
    tested: true,
  },
  'Card': {
    status: 'completed',
    file: 'semi-card.tsx',
    semiComponent: '@douyinfe/semi-ui/Card',
    priority: 'high',
    tested: true,
  },
  'Dialog': {
    status: 'completed',
    file: 'semi-dialog.tsx',
    semiComponent: '@douyinfe/semi-ui/Modal',
    priority: 'high',
    tested: true,
  },
  'Form': {
    status: 'completed',
    semiComponent: '@douyinfe/semi-ui/Form',
    priority: 'high',
    tested: true,
  },
  'Select': {
    status: 'completed',
    file: 'semi-select.tsx',
    semiComponent: '@douyinfe/semi-ui/Select',
    priority: 'high',
    tested: true,
  },
  'Tabs': {
    status: 'completed',
    file: 'semi-tabs.tsx',
    semiComponent: '@douyinfe/semi-ui/Tabs',
    priority: 'medium',
    tested: true,
  },
  'Table': {
    status: 'completed',
    file: 'semi-table.tsx',
    semiComponent: '@douyinfe/semi-ui/Table',
    priority: 'medium',
    tested: true,
  },
  'Dropdown': {
    status: 'completed',
    file: 'semi-dropdown.tsx',
    semiComponent: '@douyinfe/semi-ui/Dropdown',
    priority: 'medium',
    tested: true,
  },
  'Alert': {
    status: 'completed',
    file: 'semi-alert.tsx',
    semiComponent: '@douyinfe/semi-ui/Banner',
    priority: 'low',
    tested: true,
  },
  'Pagination': {
    status: 'completed',
    file: 'semi-pagination.tsx',
    semiComponent: '@douyinfe/semi-ui/Pagination',
    priority: 'low',
    tested: true,
  },
  'Tooltip': {
    status: 'completed',
    file: 'semi-tooltip.tsx',
    semiComponent: '@douyinfe/semi-ui/Tooltip',
    priority: 'low',
    tested: false,
  },
  'Popover': {
    status: 'completed',
    file: 'semi-popover.tsx',
    semiComponent: '@douyinfe/semi-ui/Popover',
    priority: 'low',
    tested: false,
  },
  'Checkbox': {
    status: 'completed',
    file: 'semi-checkbox.tsx',
    semiComponent: '@douyinfe/semi-ui/Checkbox',
    priority: 'medium',
    tested: false,
  },
  'Avatar': {
    status: 'completed',
    file: 'semi-avatar.tsx',
    semiComponent: '@douyinfe/semi-ui/Avatar',
    priority: 'low',
    tested: false,
  },
  'Badge': {
    status: 'completed',
    file: 'semi-badge.tsx',
    semiComponent: '@douyinfe/semi-ui/Badge',
    priority: 'low',
    tested: false,
  },
  'Skeleton': {
    status: 'completed',
    file: 'semi-skeleton.tsx',
    semiComponent: '@douyinfe/semi-ui/Skeleton',
    priority: 'low',
    tested: false,
  },
} as const

export type ComponentName = keyof typeof COMPONENT_MIGRATION_MAP

export function getMigrationStatus(componentName: ComponentName): typeof COMPONENT_MIGRATION_MAP[ComponentName] | undefined {
  return COMPONENT_MIGRATION_MAP[componentName]
}

export function isComponentMigrated(componentName: string): boolean {
  const status = COMPONENT_MIGRATION_MAP[componentName as ComponentName]
  return status?.status === 'completed'
}

export function getMigratedComponents(): ComponentName[] {
  return Object.entries(COMPONENT_MIGRATION_MAP)
    .filter(([_, value]) => value.status === 'completed')
    .map(([key]) => key as ComponentName)
}

export function getPendingComponents(): ComponentName[] {
  return Object.entries(COMPONENT_MIGRATION_MAP)
    .filter(([_, value]) => value.status === 'pending')
    .map(([key]) => key as ComponentName)
}

// ============================================================================
// BACKWARD COMPATIBILITY
// ============================================================================

export const LEGACY_IMPORT_WARNING = `
  ⚠️ DEPRECATION WARNING
  
  Importing from '@/components/ui/{component}' is deprecated.
  Please update to use '@/components/ui/semi-{component}' instead.
  
  Example:
    Before: import { Button } from '@/components/ui/button'
    After:  import { Button } from '@/components/ui'
  
  The old imports will be removed in version 2.0.0
`.trim()

export function logDeprecationWarning(componentName: string): void {
  if (process.env.NODE_ENV === 'development') {
    console.warn(`${LEGACY_IMPORT_WARNING}\nComponent: ${componentName}`)
  }
}