/**
 * Semi Skeleton Component
 * 
 * Wraps @douyinfe/semi-ui/Skeleton with backward-compatible API
 */

import * as React from "react"
import { Skeleton as SemiSkeleton } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface SkeletonProps {
  loading?: boolean
  className?: string
  style?: React.CSSProperties
  children?: React.ReactNode
  placeholder?: React.ReactNode
}

export const Skeleton: React.FC<SkeletonProps> = ({
  loading = true,
  className,
  style,
  children,
  placeholder,
  ...props
}) => {
  if (!loading) {
    return <>{children}</>
  }

  if (placeholder) {
    return <>{placeholder}</>
  }

  return (
    <SemiSkeleton
      className={cn("semi-skeleton", className)}
      style={style}
      {...props}
    />
  )
}

Skeleton.displayName = "Skeleton"

export interface SkeletonParagraphProps {
  rows?: number
  width?: string | number
  className?: string
}

export const SkeletonParagraph: React.FC<SkeletonParagraphProps> = ({
  rows = 4,
  width,
  className,
}) => {
  return (
    <SemiSkeleton.Paragraph
      rows={rows}
      width={width}
      className={cn("semi-skeleton-paragraph", className)}
    />
  )
}

SkeletonParagraph.displayName = "SkeletonParagraph"

export interface SkeletonTitleProps {
  width?: string | number
  className?: string
}

export const SkeletonTitle: React.FC<SkeletonTitleProps> = ({
  width,
  className,
}) => {
  return (
    <SemiSkeleton.Title
      width={width}
      className={cn("semi-skeleton-title", className)}
    />
  )
}

SkeletonTitle.displayName = "SkeletonTitle"

export interface SkeletonAvatarProps {
  size?: 'small' | 'medium' | 'large'
  shape?: 'circle' | 'square'
  className?: string
}

export const SkeletonAvatar: React.FC<SkeletonAvatarProps> = ({
  size = 'medium',
  shape = 'circle',
  className,
}) => {
  return (
    <SemiSkeleton.Avatar
      size={size}
      shape={shape}
      className={cn("semi-skeleton-avatar", className)}
    />
  )
}

SkeletonAvatar.displayName = "SkeletonAvatar"

export interface SkeletonImageProps {
  shape?: 'circle' | 'square' | 'rect'
  className?: string
}

export const SkeletonImage: React.FC<SkeletonImageProps> = ({
  shape = 'rect',
  className,
}) => {
  return (
    <SemiSkeleton.Image
      shape={shape}
      className={cn("semi-skeleton-image", className)}
    />
  )
}

SkeletonImage.displayName = "SkeletonImage"
