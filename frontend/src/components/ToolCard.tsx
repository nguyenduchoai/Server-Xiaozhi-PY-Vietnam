
import { memo } from "react";
import { useTranslation } from "react-i18next";
import { Info, Cloud, Music, Bell, Newspaper, Bot, Calendar, Cpu, Plug } from "lucide-react";
import { Card, Tag, Button, Typography } from "@douyinfe/semi-ui";

import type { ToolSchema, ToolCategory } from "@types";

const { Title, Text, Paragraph } = Typography;

/**
 * Category visual config — each tool type gets a unique look
 */
interface CategoryStyle {
  color: "blue" | "cyan" | "green" | "orange" | "red" | "indigo" | "purple" | "grey";
  accentColor: string;
  icon: React.ReactNode;
}

const CATEGORY_CONFIG: Record<ToolCategory, CategoryStyle> = {
  weather: {
    color: "cyan",
    accentColor: "#06b6d4",
    icon: <Cloud size={18} color="#06b6d4" />,
  },
  music: {
    color: "purple",
    accentColor: "#8b5cf6",
    icon: <Music size={18} color="#8b5cf6" />,
  },
  reminder: {
    color: "orange",
    accentColor: "#f59e0b",
    icon: <Bell size={18} color="#f59e0b" />,
  },
  news: {
    color: "blue",
    accentColor: "#3b82f6",
    icon: <Newspaper size={18} color="#3b82f6" />,
  },
  agent: {
    color: "green",
    accentColor: "#10b981",
    icon: <Bot size={18} color="#10b981" />,
  },
  calendar: {
    color: "red",
    accentColor: "#ef4444",
    icon: <Calendar size={18} color="#ef4444" />,
  },
  iot: {
    color: "indigo",
    accentColor: "#6366f1",
    icon: <Cpu size={18} color="#6366f1" />,
  },
  other: {
    color: "grey",
    accentColor: "#6b7280",
    icon: <Plug size={18} color="#6b7280" />,
  },
};

/**
 * Props for ToolCard displaying a system tool schema
 */
export interface ToolCardProps {
  tool: ToolSchema;
  onViewDetails?: (tool: ToolSchema) => void;
}

/**
 * ToolCard - Premium design with category-colored accent
 */
const ToolCardComponent = ({ tool, onViewDetails }: ToolCardProps) => {
  const { t } = useTranslation(["tools", "common"]);
  const style = CATEGORY_CONFIG[tool.category] || CATEGORY_CONFIG.other;
  const paramCount = tool.parameters?.properties ? Object.keys(tool.parameters.properties).length : 0;

  return (
    <Card
      bodyStyle={{ padding: 0 }}
      className="group relative transition-all duration-200 hover:shadow-lg h-full"
      style={{
        background: `linear-gradient(135deg, ${style.accentColor}03, ${style.accentColor}07)`,
        borderColor: `${style.accentColor}18`,
        borderLeft: `3px solid ${style.accentColor}`,
        overflow: "hidden",
      }}
    >
      <div className="p-4">
        {/* Header with Icon + Name + Category Tag */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div
              className="flex items-center justify-center w-9 h-9 rounded-lg shrink-0 transition-transform duration-200 group-hover:scale-110"
              style={{ background: `${style.accentColor}12` }}
            >
              {style.icon}
            </div>
            <Title heading={6} style={{ margin: 0 }} className="truncate flex-1">
              {tool.name}
            </Title>
          </div>
          <Tag color={style.color} type="solid" size="small" className="shrink-0 ml-2">
            {tool.category}
          </Tag>
        </div>

        {/* Description */}
        <Paragraph ellipsis={{ rows: 2, showTooltip: true }} type="secondary" className="text-sm min-h-[40px] !mb-0">
          {tool.description}
        </Paragraph>

        {/* Footer */}
        <div className="mt-3 pt-3 space-y-2" style={{ borderTop: `1px solid ${style.accentColor}10` }}>
          {/* Tool Name */}
          <div className="flex items-center justify-between">
            <Text type="tertiary" size="small">
              {t("tools:tool_name")}
            </Text>
            <code className="text-xs px-1.5 py-0.5 rounded" style={{ background: `${style.accentColor}08` }}>
              {tool.name}
            </code>
          </div>

          {/* Parameters Count */}
          {paramCount > 0 && (
            <div className="flex items-center justify-between">
              <Text type="tertiary" size="small">
                {t("tools:parameters")}
              </Text>
              <Text size="small" strong>
                {paramCount} {t("tools:params")}
              </Text>
            </div>
          )}

          {/* View Details Button */}
          {onViewDetails && (
            <div className="pt-1">
              <Button
                block
                theme="light"
                onClick={() => onViewDetails(tool)}
                icon={<Info className="h-4 w-4" />}
                style={{
                  background: `${style.accentColor}08`,
                  borderColor: `${style.accentColor}20`,
                }}
              >
                {t("common:details")}
              </Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};

export const ToolCard = memo(ToolCardComponent);
