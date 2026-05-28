import { memo, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Database, Zap, Globe, Cpu, Terminal } from "lucide-react";
import { Card, Tag, Typography } from "@douyinfe/semi-ui";

import type { McpConfig } from "@types";

const { Title, Text } = Typography;

// ============================================================================
// TRANSPORT TYPE — Visual Config
// ============================================================================

interface TransportStyle {
  accentColor: string;
  tagColor: "green" | "blue" | "cyan" | "grey";
  icon: React.ReactNode;
  label: string;
}

const TRANSPORT_STYLES: Record<string, TransportStyle> = {
  stdio: {
    accentColor: "#8b5cf6",
    tagColor: "blue",
    icon: <Terminal size={18} color="#8b5cf6" />,
    label: "STDIO",
  },
  sse: {
    accentColor: "#f59e0b",
    tagColor: "cyan",
    icon: <Zap size={18} color="#f59e0b" />,
    label: "SSE",
  },
  http: {
    accentColor: "#3b82f6",
    tagColor: "blue",
    icon: <Globe size={18} color="#3b82f6" />,
    label: "HTTP",
  },
};

const DEFAULT_TRANSPORT: TransportStyle = {
  accentColor: "#6b7280",
  tagColor: "grey",
  icon: <Database size={18} color="#6b7280" />,
  label: "Other",
};

export interface McpConfigCardProps {
  config: McpConfig;
  toolsCount?: number;
  onViewDetails: (configId: string) => void;
}

const McpConfigCardComponent = ({
  config,
  toolsCount = 0,
  onViewDetails,
}: McpConfigCardProps) => {
  const { t } = useTranslation(["mcp-configs", "common"]);
  const style = TRANSPORT_STYLES[config.type] || DEFAULT_TRANSPORT;

  const statusBadge = useMemo(
    () => ({
      color: config.is_active ? ("green" as const) : ("grey" as const),
      label: config.is_active
        ? t("status_active", "Active")
        : t("status_inactive", "Inactive"),
    }),
    [config.is_active, t]
  );

  return (
    <div onClick={() => onViewDetails(config.id)} className="h-full">
      <Card
        bodyStyle={{ padding: 0 }}
        className="cursor-pointer hover:shadow-lg transition-all duration-200 h-full group"
        style={{
          background: `linear-gradient(135deg, ${style.accentColor}03, ${style.accentColor}07)`,
          borderColor: config.is_active ? `${style.accentColor}25` : undefined,
          borderLeft: `3px solid ${style.accentColor}`,
          overflow: "hidden",
        }}
      >
        <div className="p-4">
          {/* Header */}
          <div className="flex justify-between items-start mb-3">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div
                className="flex items-center justify-center w-9 h-9 rounded-lg shrink-0 transition-transform duration-200 group-hover:scale-110"
                style={{ background: `${style.accentColor}12` }}
              >
                {style.icon}
              </div>
              <div className="min-w-0">
                <Title heading={6} style={{ margin: 0 }} className="truncate">
                  {config.name}
                </Title>
                <Text type="tertiary" size="small">{style.label}</Text>
              </div>
            </div>
            <Tag color={statusBadge.color} type="solid" size="small" className="shrink-0">
              {statusBadge.label}
            </Tag>
          </div>

          {/* Info */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Cpu className="h-3.5 w-3.5 shrink-0" style={{ color: style.accentColor }} />
              <Text type="tertiary" size="small">
                {toolsCount > 0
                  ? t("tools_count", "{{count}} tools", { count: toolsCount })
                  : t("no_tools", "No tools")}
              </Text>
            </div>

            {config.type === "sse" && config.url && (
              <div className="truncate text-xs px-2 py-1 rounded" style={{ background: `${style.accentColor}06` }}>
                <Text type="tertiary" size="small">{config.url}</Text>
              </div>
            )}

            {config.type === "stdio" && config.command && (
              <div className="truncate text-xs px-2 py-1 rounded font-mono" style={{ background: `${style.accentColor}06` }}>
                <Text type="tertiary" size="small">$ {config.command}</Text>
              </div>
            )}

            {/* Tool Tags */}
            {config.tools && config.tools.length > 0 && (
              <div className="pt-2 space-y-1" style={{ borderTop: `1px solid ${style.accentColor}10` }}>
                <Text size="small" type="tertiary" strong>
                  {t("tools", "Tools")}:
                </Text>
                <div className="flex flex-wrap gap-1">
                  {config.tools.slice(0, 5).map((tool) => (
                    <Tag key={tool.name} size="small" type="light" color={style.tagColor}>
                      {tool.name}
                    </Tag>
                  ))}
                  {config.tools.length > 5 && (
                    <Tag size="small" type="ghost" color="grey">
                      +{config.tools.length - 5} {t("more", "more")}
                    </Tag>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

export const McpConfigCard = memo(McpConfigCardComponent);
