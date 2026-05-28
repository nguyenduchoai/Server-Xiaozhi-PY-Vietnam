/**
 * ProviderCard - Premium Enterprise Design
 * Color-coded cards with left accent border, gradient tints, and category icons
 * for instant visual identification of provider types.
 */

import { memo } from "react";
import { useTranslation } from "react-i18next";

import type { Provider, ProviderCategory } from "@types";
import { useAuth } from "@/hooks/useAuth";
import { Card, Tag, Button, Dropdown, Typography } from "@douyinfe/semi-ui";
import { IconMore, IconEdit, IconDelete } from "@douyinfe/semi-icons";
import { Cpu, Volume2, Mic, Brain, Zap, MessageSquare, Eye } from "lucide-react";

const { Text, Title } = Typography;

// ============================================================================
// DESIGN SYSTEM — Provider Category Visual Config
// ============================================================================

interface CategoryStyle {
  tagColor: "blue" | "purple" | "green" | "orange" | "pink" | "cyan" | "indigo";
  accentColor: string;
  bgGradient: string;
  borderColor: string;
  iconBg: string;
  icon: React.ReactNode;
  emoji: string;
}

const CATEGORY_STYLES: Record<ProviderCategory, CategoryStyle> = {
  LLM: {
    tagColor: "blue",
    accentColor: "#6366f1",
    bgGradient: "linear-gradient(135deg, rgba(99,102,241,0.03), rgba(99,102,241,0.08))",
    borderColor: "rgba(99,102,241,0.20)",
    iconBg: "rgba(99,102,241,0.10)",
    icon: <Cpu size={18} color="#6366f1" />,
    emoji: "🧠",
  },
  VLLM: {
    tagColor: "indigo",
    accentColor: "#8b5cf6",
    bgGradient: "linear-gradient(135deg, rgba(139,92,246,0.03), rgba(139,92,246,0.08))",
    borderColor: "rgba(139,92,246,0.20)",
    iconBg: "rgba(139,92,246,0.10)",
    icon: <Eye size={18} color="#8b5cf6" />,
    emoji: "👁️",
  },
  TTS: {
    tagColor: "green",
    accentColor: "#06b6d4",
    bgGradient: "linear-gradient(135deg, rgba(6,182,212,0.03), rgba(6,182,212,0.08))",
    borderColor: "rgba(6,182,212,0.20)",
    iconBg: "rgba(6,182,212,0.10)",
    icon: <Volume2 size={18} color="#06b6d4" />,
    emoji: "🔊",
  },
  ASR: {
    tagColor: "purple",
    accentColor: "#f59e0b",
    bgGradient: "linear-gradient(135deg, rgba(245,158,11,0.03), rgba(245,158,11,0.08))",
    borderColor: "rgba(245,158,11,0.20)",
    iconBg: "rgba(245,158,11,0.10)",
    icon: <Mic size={18} color="#f59e0b" />,
    emoji: "🎙️",
  },
  VAD: {
    tagColor: "orange",
    accentColor: "#f97316",
    bgGradient: "linear-gradient(135deg, rgba(249,115,22,0.03), rgba(249,115,22,0.08))",
    borderColor: "rgba(249,115,22,0.20)",
    iconBg: "rgba(249,115,22,0.10)",
    icon: <Zap size={18} color="#f97316" />,
    emoji: "⚡",
  },
  Memory: {
    tagColor: "pink",
    accentColor: "#10b981",
    bgGradient: "linear-gradient(135deg, rgba(16,185,129,0.03), rgba(16,185,129,0.08))",
    borderColor: "rgba(16,185,129,0.20)",
    iconBg: "rgba(16,185,129,0.10)",
    icon: <Brain size={18} color="#10b981" />,
    emoji: "💡",
  },
  Intent: {
    tagColor: "cyan",
    accentColor: "#ef4444",
    bgGradient: "linear-gradient(135deg, rgba(239,68,68,0.03), rgba(239,68,68,0.08))",
    borderColor: "rgba(239,68,68,0.20)",
    iconBg: "rgba(239,68,68,0.10)",
    icon: <MessageSquare size={18} color="#ef4444" />,
    emoji: "🎯",
  },
};

const DEFAULT_STYLE: CategoryStyle = {
  tagColor: "blue",
  accentColor: "#6b7280",
  bgGradient: "none",
  borderColor: "var(--apple-border-primary)",
  iconBg: "rgba(107,114,128,0.10)",
  icon: <Cpu size={18} color="#6b7280" />,
  emoji: "📦",
};

// ============================================================================
// COMPONENT
// ============================================================================

export interface ProviderCardProps {
  provider: Provider;
  onView?: (provider: Provider) => void;
  onEdit?: (provider: Provider) => void;
  onDelete?: (provider: Provider) => void;
  onToggleActive?: (provider: Provider) => void;
  onClick?: (provider: Provider) => void;
}

const ProviderCardComponent = ({
  provider,
  onView,
  onEdit,
  onDelete,
  onClick,
}: ProviderCardProps) => {
  const { t } = useTranslation(["providers", "common"]);
  const { user } = useAuth();
  const isSuperAdmin = user?.is_superuser === true;

  const style = CATEGORY_STYLES[provider.category] || DEFAULT_STYLE;
  const isDefaultProvider = provider.source === "default" || provider.source === "public" || provider.is_public === true;

  const canEdit = isSuperAdmin || (!isDefaultProvider && Boolean(onEdit));
  const canDelete = !isDefaultProvider && (isSuperAdmin || Boolean(onDelete));

  const handleCardClick = () => {
    if (onClick) {
      onClick(provider);
    } else if (onView) {
      onView(provider);
    }
  };

  const handleEditClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(provider);
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(provider);
  };

  return (
    <div onClick={handleCardClick} className="cursor-pointer h-full">
      <Card
        className="group relative transition-all duration-200 hover:shadow-lg h-full"
        bodyStyle={{ padding: 0 }}
        style={{
          background: style.bgGradient,
          borderColor: style.borderColor,
          borderLeft: `3px solid ${style.accentColor}`,
          overflow: "hidden",
          height: "100%",
        }}
      >
        <div className="p-4">
          {/* Action Menu */}
          {(canEdit || canDelete) && (
            <div className="absolute top-3 right-3 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
              <Dropdown
                trigger="click"
                position="bottomRight"
                clickToHide
                render={
                  <Dropdown.Menu>
                    {canEdit && (
                      <Dropdown.Item onClick={handleEditClick}>
                        <IconEdit className="mr-2" />
                        {t("common:edit")}
                      </Dropdown.Item>
                    )}
                    {canEdit && canDelete && <Dropdown.Divider />}
                    {canDelete && (
                      <Dropdown.Item type="danger" onClick={handleDeleteClick}>
                        <IconDelete className="mr-2" />
                        {t("common:delete")}
                      </Dropdown.Item>
                    )}
                  </Dropdown.Menu>
                }
              >
                <Button
                  icon={<IconMore />}
                  theme="borderless"
                  type="tertiary"
                  size="small"
                  onClick={(e) => e.stopPropagation()}
                />
              </Dropdown>
            </div>
          )}

          {/* Tags Row */}
          <div className="flex items-center gap-2 flex-wrap mb-3">
            <Tag color={style.tagColor} size="small" type="solid">
              {provider.category}
            </Tag>
            {provider.source && (
              <Tag
                color={isDefaultProvider ? "amber" : "grey"}
                size="small"
              >
                {isDefaultProvider ? t("providers:default") : t("providers:custom")}
              </Tag>
            )}
            <Tag
              color={provider.is_active ? "green" : "grey"}
              size="small"
            >
              {provider.is_active ? t("common:active") : t("common:inactive")}
            </Tag>
          </div>

          {/* Name with Icon */}
          <div className="flex items-center gap-3 mb-3">
            <div
              className="flex items-center justify-center w-9 h-9 rounded-lg shrink-0 transition-transform duration-200 group-hover:scale-110"
              style={{ background: style.iconBg }}
            >
              {style.icon}
            </div>
            <Title heading={5} className="!mb-0 line-clamp-2 flex-1">
              {provider.name}
            </Title>
          </div>

          {/* Content */}
          <div className="space-y-1.5 pl-12">
            <div className="flex items-center justify-between">
              <Text type="tertiary" size="small">{t("providers:type")}</Text>
              <Text strong size="small" className="truncate ml-2">{provider.type}</Text>
            </div>

            {typeof provider.config.model_name === "string" && (
              <div className="flex items-center justify-between gap-2">
                <Text type="tertiary" size="small">{t("providers:model")}</Text>
                <code className="text-xs truncate px-1.5 py-0.5 rounded" style={{ background: `${style.accentColor}10` }}>
                  {provider.config.model_name}
                </code>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

export const ProviderCard = memo(ProviderCardComponent);
