
import { memo, useMemo } from "react";
import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { IconClock, IconArticle } from "@douyinfe/semi-icons";
import { Card, Badge, Button, Row, Col, Typography, Space } from "@douyinfe/semi-ui";
import { Bot, Wifi, WifiOff, Settings2, BookMarked } from "lucide-react";

import type { Agent } from "@types";

const { Title, Text } = Typography;

const formatTimestamp = (value?: string | null) => {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "short",
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

// ============================================================================
// VISUAL STATES — Each readiness level gets a unique visual treatment
// ============================================================================

interface ReadinessStyle {
  accentColor: string;
  bgGradient: string;
  borderColor: string;
  statusDot: string;
  label: string;
}

export interface AgentCardProps {
  agent: Agent;
  className?: string;
  onClick?: (agent: Agent) => void;
}

const AgentCardComponent = ({ agent, className, onClick }: AgentCardProps) => {
  const { t } = useTranslation("agents");
  const navigate = useNavigate();
  const isReady = Boolean(agent.device_id && (agent.active_template_id || agent.LLM || agent.TTS));
  const hasDevice = Boolean(agent.device_id);
  const hasTemplate = Boolean(agent.active_template_id || agent.LLM || agent.TTS);
  const clickable = typeof onClick === "function";

  // Determine visual style based on readiness
  const readinessStyle = useMemo((): ReadinessStyle => {
    if (isReady) {
      return {
        accentColor: "#10b981",
        bgGradient: "linear-gradient(135deg, rgba(16,185,129,0.02), rgba(16,185,129,0.06))",
        borderColor: "rgba(16,185,129,0.18)",
        statusDot: "#10b981",
        label: t("active"),
      };
    }
    if (hasDevice || hasTemplate) {
      return {
        accentColor: "#f59e0b",
        bgGradient: "linear-gradient(135deg, rgba(245,158,11,0.02), rgba(245,158,11,0.05))",
        borderColor: "rgba(245,158,11,0.15)",
        statusDot: "#f59e0b",
        label: t("inactive"),
      };
    }
    return {
      accentColor: "#94a3b8",
      bgGradient: "linear-gradient(135deg, rgba(148,163,184,0.02), rgba(148,163,184,0.04))",
      borderColor: "rgba(148,163,184,0.15)",
      statusDot: "#94a3b8",
      label: t("inactive"),
    };
  }, [isReady, hasDevice, hasTemplate, t]);

  const statusType = agent.status === "enabled" ? "success" : "secondary";

  const handleClick = () => {
    if (!clickable) return;
    onClick?.(agent);
  };

  const handleHistoryClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/agents/${agent.id}/history`);
  };

  const handleKnowledgeClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/agents/${agent.id}/knowledge`);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!clickable) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick?.(agent);
    }
  };

  return (
    <div
      className={`cursor-pointer h-full transition-all ${className}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
    >
      <Card
        shadows="hover"
        style={{
          height: '100%',
          background: readinessStyle.bgGradient,
          borderColor: readinessStyle.borderColor,
          borderLeft: `3px solid ${readinessStyle.accentColor}`,
        }}
        bodyStyle={{ padding: 24 }}
        footerLine={true}
        footer={
          <div className="flex justify-between items-center w-full pt-4">
            <Space>
              <Button icon={<IconClock />} theme="borderless" type="tertiary" onClick={handleHistoryClick}>
                {t("history", "History")}
              </Button>
              <Button icon={<IconArticle />} theme="borderless" type="tertiary" onClick={handleKnowledgeClick}>
                {t("knowledge_base", "Knowledge")}
              </Button>
            </Space>
            <Text size="small" type="tertiary">
              {formatTimestamp(agent.updated_at)}
            </Text>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Header with Avatar + Status */}
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-3 flex-1 pr-4">
              {/* Agent Avatar */}
              <div
                className="flex items-center justify-center w-11 h-11 rounded-xl shrink-0"
                style={{
                  background: `linear-gradient(135deg, ${readinessStyle.accentColor}15, ${readinessStyle.accentColor}30)`,
                }}
              >
                <Bot size={22} color={readinessStyle.accentColor} />
              </div>
              <div className="min-w-0">
                <Title heading={5} style={{ marginBottom: 2 }} className="truncate">
                  {agent.agent_name}
                </Title>
                <Text type="secondary" className="line-clamp-1 text-sm">
                  {agent.description || t("agent_description")}
                </Text>
              </div>
            </div>
            {/* Status Indicator */}
            <div className="flex items-center gap-2 shrink-0">
              <div
                className="w-2.5 h-2.5 rounded-full animate-pulse"
                style={{ background: readinessStyle.statusDot }}
              />
              <Text size="small" strong style={{ color: readinessStyle.accentColor }}>
                {readinessStyle.label}
              </Text>
            </div>
          </div>

          {/* Status & ID Badges */}
          <Space>
            <Badge type={statusType}>{agent.status}</Badge>
            <Badge type="tertiary">{formatIdentifier(agent.id)}</Badge>
          </Space>

          {/* Readiness Grid — Clear visual state for each config slot */}
          <Row gutter={[12, 12]}>
            <Col span={12}>
              <div
                className="p-3 rounded-lg border transition-all"
                style={{
                  background: hasDevice
                    ? "linear-gradient(135deg, rgba(59,130,246,0.04), rgba(59,130,246,0.10))"
                    : "var(--apple-surface-tertiary)",
                  borderColor: hasDevice ? "rgba(59,130,246,0.25)" : "var(--apple-border-primary)",
                  borderStyle: hasDevice ? "solid" : "dashed",
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  {hasDevice ? (
                    <Wifi size={14} color="#3b82f6" />
                  ) : (
                    <WifiOff size={14} color="var(--apple-text-quaternary)" />
                  )}
                  <Text size="small" type="secondary" strong style={{ textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.05em' }}>
                    {t("device_type")}
                  </Text>
                </div>
                <Text size="small" strong={hasDevice} type={hasDevice ? 'primary' : 'quaternary'}>
                  {hasDevice ? t('configured') : t('not_configured')}
                </Text>
              </div>
            </Col>
            <Col span={12}>
              <div
                className="p-3 rounded-lg border transition-all"
                style={{
                  background: hasTemplate
                    ? "linear-gradient(135deg, rgba(139,92,246,0.04), rgba(139,92,246,0.10))"
                    : "var(--apple-surface-tertiary)",
                  borderColor: hasTemplate ? "rgba(139,92,246,0.25)" : "var(--apple-border-primary)",
                  borderStyle: hasTemplate ? "solid" : "dashed",
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  {hasTemplate ? (
                    <BookMarked size={14} color="#8b5cf6" />
                  ) : (
                    <Settings2 size={14} color="var(--apple-text-quaternary)" />
                  )}
                  <Text size="small" type="secondary" strong style={{ textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.05em' }}>
                    {t("templates")}
                  </Text>
                </div>
                <Text size="small" strong={hasTemplate} style={{ color: hasTemplate ? '#8b5cf6' : undefined }} type={hasTemplate ? undefined : 'quaternary'}>
                  {hasTemplate ? t('configured') : t('not_configured')}
                </Text>
              </div>
            </Col>
          </Row>
        </div>
      </Card>
    </div>
  );
};

export const AgentCard = memo(AgentCardComponent);
