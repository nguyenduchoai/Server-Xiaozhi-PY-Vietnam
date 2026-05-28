/**
 * Semi Table Component
 * 
 * Wraps @douyinfe/semi-ui/Table with enhanced features and styling.
 */

import * as React from "react"
import { Table as SemiTable } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface TableProps<T = any> {
  className?: string
  columns?: ColumnProps<T>[]
  dataSource?: T[]
  loading?: boolean
  pagination?: boolean | object
  [key: string]: any
}

const Table = React.forwardRef<any, TableProps>(
  ({ className, columns, dataSource, loading, pagination, style, ...props }, ref) => {
    return (
      <SemiTable
        ref={ref}
        className={cn("semi-table", className)}
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        pagination={pagination}
        style={{
          borderRadius: 'var(--radius)',
          ...style,
        }}
        {...props}
      />
    )
  }
)
Table.displayName = "Table"

export interface ColumnProps<T = any> {
  title?: React.ReactNode
  dataIndex?: string
  key?: string
  render?: (value: any, record: T, index: number) => React.ReactNode
  width?: number | string
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  filter?: React.ReactNode | ((value: any, record: T) => boolean)
  [key: string]: void | any
}

const Column = <T extends object>(props: ColumnProps<T>) => props

export { Table, Column }