/**
 * Semi Tabs Component
 * 
 * Wraps @douyinfe/semi-ui/Tabs with enhanced styling and features.
 */

import * as React from "react"
import { Tabs as SemiTabs, TabPane as SemiTabPane } from "@douyinfe/semi-ui"
type SemiTabsProps = any;
type SemiTabPaneProps = any;
import { cn } from "@/lib/utils"

export interface TabsProps {
  className?: string
  children?: React.ReactNode
  [key: string]: any
}

export interface TabPaneProps {
  tab?: React.ReactNode
  className?: string
  children?: React.ReactNode
  [key: string]: any
}

const Tabs = React.forwardRef<any, TabsProps>(
  ({ className, style, children, ...props }, ref) => {
    return (
      <SemiTabs
        ref={ref}
        className={cn("semi-tabs", className)}
        style={{
          ...style,
        }}
        {...props}
      >
        {children}
      </SemiTabs>
    )
  }
)
Tabs.displayName = "Tabs"

const TabPane = React.forwardRef<any, TabPaneProps>(
  ({ tab, className, children, ...props }, ref) => {
    return (
      <SemiTabPane
        ref={ref}
        tab={tab}
        className={cn("tab-pane", className)}
        {...props}
      >
        {children}
      </SemiTabPane>
    )
  }
)
TabPane.displayName = "TabPane"

export { Tabs, TabPane }