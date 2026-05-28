/**
 * AgentDetailCard - Semi Design implementation
 * Displays agent details in a card format
 */

import { memo, useCallback, useState } from "react";
import { User } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { Agent, AgentDetail } from "@types";
import { CHAT_HISTORY_CONF_LABELS } from "@types";
import {
  Card,
  Typography,
  Tag,
  Button,
  Skeleton,
  Empty,
} from "@douyinfe/semi-ui";
import { IconCopy, IconTick, IconPlus } from "@douyinfe/semi-icons";

const { Text, Title, Paragraph } = Typography;

const formatTimestamp = (value?: string | null) => {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
};

const formatIdentifier = (value?: string | null) => {
  if (!value) return "—";
  return value.length > 10 ? `${value.slice(0, 4)}…${value.slice(-4)}` : value;
};

export interface AgentDetailCardProps {
  agent?: Agent | AgentDetail | null;
  className?: string;
  isLoading?: boolean;
  onAddDevice?: () => void;
}

interface CopyState {
  copied: boolean;
  field: string | null;
}

const AgentDetailCardComponent = ({
  agent,
  className,
  isLoading = false,
  onAddDevice,
}: AgentDetailCardProps) => {
  const [copyState, setCopyState] = useState<CopyState>({
    copied: false,
    field: null,
  });
  const { t } = useTranslation("agents");

  const handleCopy = useCallback((text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopyState({ copied: true, field });
    setTimeout(() => {
      setCopyState({ copied: false, field: null });
    }, 2000);
  }, []);

  if (isLoading) {
    return (
      <Card className={className}>
        <Skeleton.Title style={{ marginBottom: 16 }} />
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton.Paragraph key={i} rows={1} />
          ))}
        </div>
      </Card>
    );
  }

  if (!agent) {
    return (
      <Card className={className}>
        <Empty title="No agent data available" />
      </Card>
    );
  }

  const CopyButton = ({ text, field }: { text: string; field: string }) => (
    <Button
      icon={
        copyState.copied && copyState.field === field ? (
          <IconTick className="text-green-500" />
        ) : (
          <IconCopy />
        )
      }
      theme="borderless"
      type="tertiary"
      size="small"
      onClick={() => handleCopy(text, field)}
    />
  );

  return (
    <Card
      className={className}
      title={
        <div>
          <Title heading={6} className="!mb-0">{t("agent_details")}</Title>
          <Text type="tertiary" size="small">{t("agent_details_desc")}</Text>
        </div>
      }
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Agent ID */}
        <div className="space-y-1">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("agent_id")}
          </Text>
          <div className="flex items-center gap-1">
            <code className="text-xs font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded flex-1 truncate">
              {formatIdentifier(agent.id)}
            </code>
            <CopyButton text={agent.id} field="id" />
          </div>
        </div>

        {/* Name */}
        <div className="space-y-1">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("name")}
          </Text>
          <Text className="block">{agent.agent_name || "—"}</Text>
        </div>

        {/* Status */}
        <div className="space-y-1">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("agent_status")}
          </Text>
          <Tag color={agent.status === "enabled" ? "green" : "grey"} size="small">
            {agent.status}
          </Tag>
        </div>

        {/* Chat History Config */}
        <div className="space-y-1">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("chat_history_conf", "Chat History")}
          </Text>
          <Text className="block text-sm">
            {agent.chat_history_conf !== undefined
              ? CHAT_HISTORY_CONF_LABELS[agent.chat_history_conf as 0 | 1 | 2]
              : CHAT_HISTORY_CONF_LABELS[0]}
          </Text>
        </div>

        {/* Description */}
        <div className="space-y-1 sm:col-span-2 lg:col-span-3">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("agent_description")}
          </Text>
          <Paragraph ellipsis={{ rows: 1 }} className="text-sm !mb-0">
            {agent.description || t("no_description")}
          </Paragraph>
        </div>

        {/* User Profile */}
        {agent.user_profile && (
          <div className="space-y-1 sm:col-span-2 lg:col-span-3">
            <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
              {t("user_profile") || "User Profile"}
            </Text>
            <div className="flex items-start gap-2">
              <User className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
              <Paragraph className="text-sm !mb-0 whitespace-pre-wrap">
                {agent.user_profile}
              </Paragraph>
            </div>
          </div>
        )}

        {/* Device ID */}
        <div className="space-y-1">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("device")}
          </Text>
          {agent.device_id ? (
            <div className="flex items-center gap-1">
              <code className="text-xs font-mono bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded flex-1 truncate">
                {formatIdentifier(agent.device_id)}
              </code>
              <CopyButton text={agent.device_id} field="device" />
            </div>
          ) : (
            <Button
              icon={<IconPlus />}
              size="small"
              theme="light"
              onClick={onAddDevice}
            >
              {t("add_device")}
            </Button>
          )}
        </div>

        {/* Template ID */}
        <div className="space-y-1">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("template_singular")}
          </Text>
          {agent.active_template_id ? (
            <div className="flex items-center gap-1">
              <code className="text-xs font-mono bg-purple-50 dark:bg-purple-900/20 px-2 py-1 rounded flex-1 truncate">
                {formatIdentifier(agent.active_template_id)}
              </code>
              <CopyButton text={agent.active_template_id} field="template" />
            </div>
          ) : (
            <Text type="tertiary" size="small">{t("device_not_assigned")}</Text>
          )}
        </div>

        {/* Created At */}
        <div className="space-y-1">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("agent_created")}
          </Text>
          <Text size="small">{formatTimestamp(agent.created_at)}</Text>
        </div>

        {/* Updated At */}
        <div className="space-y-1">
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold">
            {t("agent_updated")}
          </Text>
          <Text size="small">{formatTimestamp(agent.updated_at)}</Text>
        </div>
      </div>
    </Card>
  );
};

export const AgentDetailCard = memo(AgentDetailCardComponent);
