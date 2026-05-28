/**
 * Semi Pagination Component
 * 
 * Wraps @douyinfe/semi-ui/Pagination with enhanced styling.
 */

import * as React from "react"
import { Pagination as SemiPagination } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface PaginationProps {
  className?: string
  current?: number
  total?: number
  pageSize?: number
  showTotal?: boolean
  onChange?: (page: number, pageSize: number) => void
  [key: string]: any
}

const Pagination = React.forwardRef<any, PaginationProps>(
  ({ className, current, total, pageSize, showTotal = true, onChange, style, ...props }, ref) => {
    const handlePageChange = (page: number) => {
      onChange?.(page, pageSize || 10)
    }

    return (
      <SemiPagination
        ref={ref}
        className={cn("semi-pagination", className)}
        currentPage={current}
        total={total}
        pageSize={pageSize}
        showTotal={showTotal}
        onPageChange={handlePageChange}
        style={{
          ...style,
        }}
        {...props}
      />
    )
  }
)
Pagination.displayName = "Pagination"

export { Pagination }