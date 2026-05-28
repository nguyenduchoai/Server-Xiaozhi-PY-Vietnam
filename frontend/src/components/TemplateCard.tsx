
import { memo } from "react";
import { IconEdit, IconDelete, IconGlobe } from "@douyinfe/semi-icons";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Card, Button, Typography, Tag, Space } from "@douyinfe/semi-ui";
import { FileText, Cpu, Volume2, Mic } from "lucide-react";

import type { Template } from "@types";

const { Title, Paragraph, Text } = Typography;

const truncateText = (text: string, maxLength: number = 150) => {
  if (!text) return "N/A";
  return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text;
};

// Provider tag color mapping
const MODEL_COLORS: Record<string, { color: string; tagColor: "indigo" | "cyan" | "amber" }> = {
  LLM: { color: "#6366f1", tagColor: "indigo" },
  TTS: { color: "#06b6d4", tagColor: "cyan" },
  ASR: { color: "#f59e0b", tagColor: "amber" },
};

export interface TemplateCardProps {
  template: Template;
  className?: string;
  onEdit?: () => void;
  onDelete?: () => void;
  onClick?: () => void;
}

const TemplateCardComponent = ({
  template,
  className,
  onEdit,
  onDelete,
  onClick,
}: TemplateCardProps) => {
  const { t } = useTranslation("templates");
  const navigate = useNavigate();

  const modelsList = [
    { label: "LLM", value: template.LLM?.name, icon: <Cpu size={12} color="#6366f1" /> },
    { label: "TTS", value: template.TTS?.name, icon: <Volume2 size={12} color="#06b6d4" /> },
    { label: "ASR", value: template.ASR?.name, icon: <Mic size={12} color="#f59e0b" /> },
  ].filter((item) => item.value);

  const handleCardClick = () => {
    if (onClick) {
      onClick();
    } else {
      navigate(`/templates/${template.id}`);
    }
  };

  // Determine accent based on how many providers are configured
  const configCount = modelsList.length;
  const accentColor = configCount >= 3 ? "#10b981" : configCount >= 1 ? "#6366f1" : "#94a3b8";

  return (
    <div
      onClick={handleCardClick}
      className={`group relative cursor-pointer transition-all duration-200 ${className}`}
    >
      <Card
        shadows="hover"
        bodyStyle={{ padding: 0 }}
        style={{
          background: `linear-gradient(135deg, ${accentColor}03, ${accentColor}06)`,
          borderColor: `${accentColor}18`,
          borderLeft: `3px solid ${accentColor}`,
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div className="px-4 pt-4 pb-2 flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div
              className="flex items-center justify-center w-9 h-9 rounded-lg shrink-0 transition-transform duration-200 group-hover:scale-110"
              style={{ background: `${accentColor}12` }}
            >
              <FileText size={18} color={accentColor} />
            </div>
            <div className="flex-1 overflow-hidden">
              <Title heading={5} ellipsis={{ showTooltip: true }} className="!mb-0">
                {template.name}
              </Title>
            </div>
          </div>
          <Space className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
            {onEdit && (
              <Button icon={<IconEdit />} theme="borderless" size="small" onClick={(e) => { e.stopPropagation(); onEdit(); }} />
            )}
            {onDelete && (
              <Button icon={<IconDelete />} theme="borderless" type="danger" size="small" onClick={(e) => { e.stopPropagation(); onDelete(); }} />
            )}
          </Space>
        </div>

        {/* Content */}
        <div className="px-4 pb-4 space-y-3">
          <Paragraph ellipsis={{ rows: 2 }} type="secondary" className="!mb-0 text-sm min-h-[40px]">
            {truncateText(template.prompt, 100)}
          </Paragraph>

          {/* Provider Tags — Color-coded */}
          <div className="flex flex-wrap gap-1.5">
            {modelsList.map((model) => {
              const cfg = MODEL_COLORS[model.label] || { tagColor: "grey" as any };
              return (
                <Tag key={model.label} color={cfg.tagColor} type="light" size="small">
                  <span className="flex items-center gap-1">
                    {model.icon}
                    {model.label}: {model.value}
                  </span>
                </Tag>
              );
            })}
          </div>

          {/* Footer */}
          <div className="pt-2 border-t flex items-center justify-between" style={{ borderColor: `${accentColor}12` }}>
            {template.is_public ? (
              <Tag color="cyan" type="light" size="small" prefixIcon={<IconGlobe />}>
                {t("public")}
              </Tag>
            ) : (
              <Text type="quaternary" size="small">Private</Text>
            )}
            {configCount > 0 && (
              <Text type="tertiary" size="small">{configCount}/3 providers</Text>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

export const TemplateCard = memo(TemplateCardComponent);
