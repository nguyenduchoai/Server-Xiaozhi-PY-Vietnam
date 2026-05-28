/**
 * KnowledgeSectorBadge - Semi Design implementation
 */

import { Tag } from "@douyinfe/semi-ui";
import type { MemorySector } from "@/types";
import { Calendar, BookOpen, Cog, Heart, Lightbulb } from "lucide-react";

type SectorConfig = {
  label: string;
  labelVi: string;
  color: "blue" | "green" | "purple" | "pink" | "amber" | "orange";
  icon: React.ElementType;
};

const SECTOR_CONFIG: Record<MemorySector, SectorConfig> = {
  episodic: {
    label: "Episodic",
    labelVi: "Sự kiện",
    color: "blue",
    icon: Calendar,
  },
  semantic: {
    label: "Semantic",
    labelVi: "Kiến thức",
    color: "green",
    icon: BookOpen,
  },
  procedural: {
    label: "Procedural",
    labelVi: "Quy trình",
    color: "purple",
    icon: Cog,
  },
  emotional: {
    label: "Emotional",
    labelVi: "Cảm xúc",
    color: "pink",
    icon: Heart,
  },
  reflective: {
    label: "Reflective",
    labelVi: "Suy nghĩ",
    color: "amber",
    icon: Lightbulb,
  },
};

type KnowledgeSectorBadgeProps = {
  sector: MemorySector;
  showIcon?: boolean;
  onClick?: () => void;
  isActive?: boolean;
  locale?: "en" | "vi";
  className?: string;
};

export const KnowledgeSectorBadge = ({
  sector,
  showIcon = true,
  onClick,
  isActive = false,
  locale = "en",
  className,
}: KnowledgeSectorBadgeProps) => {
  const config = SECTOR_CONFIG[sector];
  const Icon = config.icon;
  const label = locale === "vi" ? config.labelVi : config.label;

  return (
    <Tag
      color={config.color}
      size="small"
      className={`${className || ""} ${onClick ? "cursor-pointer" : ""} ${isActive ? "ring-2 ring-offset-1 ring-blue-500" : ""}`}
      onClick={onClick}
    >
      <span className="flex items-center gap-1">
        {showIcon && <Icon className="h-3 w-3" />}
        {label}
      </span>
    </Tag>
  );
};

export const getSectorConfig = (sector: MemorySector) => SECTOR_CONFIG[sector];
export const ALL_SECTORS: MemorySector[] = [
  "episodic",
  "semantic",
  "procedural",
  "emotional",
  "reflective",
];
