/**
 * Semi Avatar Component
 * 
 * Wraps @douyinfe/semi-ui/Avatar with backward-compatible API
 */

import * as React from "react"
import { Avatar as SemiAvatar } from "@douyinfe/semi-ui"
import { cn } from "@/lib/utils"

export interface AvatarProps {
  src?: string
  alt?: string
  size?: 'small' | 'medium' | 'large' | number
  shape?: 'circle' | 'square'
  className?: string
  style?: React.CSSProperties
  children?: React.ReactNode
  hoverMask?: React.ReactNode
  onClick?: () => void
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt,
  size = 'medium',
  shape = 'circle',
  className,
  style,
  children,
  hoverMask,
  onClick,
  ...props
}) => {
  const sizeMap = {
    small: 'small',
    medium: 'medium',
    large: 'large',
  }

  const resolvedSize = typeof size === 'number' ? size : sizeMap[size] || 'medium'

  return (
    <SemiAvatar
      src={src}
      alt={alt}
      size={resolvedSize}
      shape={shape}
      className={cn("semi-avatar", className)}
      style={style}
      onClick={onClick}
      {...props}
    >
      {children}
    </SemiAvatar>
  )
}

Avatar.displayName = "Avatar"

export interface AvatarGroupProps {
  children?: React.ReactNode
  size?: AvatarProps['size']
  maxCount?: number
  overlapGap?: number
  renderMore?: (restNum: number) => React.ReactNode
  className?: string
}

export const AvatarGroup: React.FC<AvatarGroupProps> = ({
  children,
  size,
  maxCount,
  overlapGap,
  renderMore,
  className,
  ...props
}) => {
  return (
    <SemiAvatar.Group
      size={size as any}
      maxCount={maxCount}
      overlapGap={overlapGap}
      renderMore={renderMore}
      className={cn("semi-avatar-group", className)}
      {...props}
    >
      {children}
    </SemiAvatar.Group>
  )
}

AvatarGroup.displayName = "AvatarGroup"
