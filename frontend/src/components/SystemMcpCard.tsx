"use client";

import { memo, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Cpu, Database, Zap } from "lucide-react";
import { Card, Tag, Typography } from "@douyinfe/semi-ui";

import type { SystemMcpServer } from "@types";
import { cn } from "@/lib/utils";

const { Title, Text, Paragraph } = Typography;

export interface SystemMcpCardProps {
  server: SystemMcpServer;
  toolsCount?: number;
  onViewDetails: (serverName: string) => void;
}

const getTransportIcon = (type: string) => {
  switch (type) {
    case "stdio":
      return <Database className="h-4 w-4" />;
    case "sse":
      return <Zap className="h-4 w-4" />;
    case "http":
      return <Cpu className="h-4 w-4" />;
    default:
      return <Cpu className="h-4 w-4" />;
  }
};

const SystemMcpCardComponent = ({
  server,
  toolsCount = 0,
  onViewDetails,
}: SystemMcpCardProps) => {
  const { t } = useTranslation(["mcp-configs", "common"]);

  const statusBadge = useMemo(
    () => ({
      color: server.is_active ? ("blue" as const) : ("grey" as const),
      label: server.is_active
        ? t("status_active", "Active")
        : t("status_inactive", "Inactive"),
    }),
    [server.is_active, t]
  );

  return (
    <div onClick={() => onViewDetails(server.name)} className="h-full">
      <Card
        bodyStyle={{ padding: 16 }}
        className={cn(
          "cursor-pointer hover:shadow-lg transition-all h-full",
          server.is_active && "border-blue-200"
        )}
        title={
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              <div>
                <Title heading={6} style={{ margin: 0 }}>{server.name}</Title>
                <Text type="tertiary" size="small">{server.type}</Text>
              </div>
            </div>
            <Tag color={statusBadge.color} type="solid">{statusBadge.label}</Tag>
          </div>
        }
      >
        <div className="space-y-3 mt-2">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              {getTransportIcon(server.type)}
              <Text strong className="capitalize">{server.type}</Text>
            </div>
            <div className="flex items-center gap-1">
              <Cpu className="h-3.5 w-3.5 text-gray-500" />
              <Text type="tertiary">
                {toolsCount > 0
                  ? t("tools_count", "{{count}} tools", { count: toolsCount })
                  : t("no_tools", "No tools")}
              </Text>
            </div>
          </div>

          {server.type === "sse" && server.url && (
            <div className="truncate text-xs text-gray-500">
              <Text strong>URL:</Text> {server.url}
            </div>
          )}

          {server.type === "http" && server.url && (
            <div className="truncate text-xs text-gray-500">
              <Text strong>URL:</Text> {server.url}
            </div>
          )}

          {server.type === "stdio" && server.command && (
            <div className="truncate text-xs text-gray-500">
              <Text strong>Command:</Text> {server.command}
            </div>
          )}

          {server.description && (
            <Paragraph ellipsis={{ rows: 2 }} className="text-xs text-gray-500">
              {server.description}
            </Paragraph>
          )}
        </div>
      </Card>
    </div>
  );
};

export const SystemMcpCard = memo(SystemMcpCardComponent);

