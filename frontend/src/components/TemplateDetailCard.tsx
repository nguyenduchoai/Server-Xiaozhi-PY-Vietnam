/**
 * TemplateDetailCard - Semi Design implementation
 */

import { memo } from "react";
import { LayoutTemplate } from "lucide-react";

import type { AgentTemplate } from "@types";
import { Card, Typography, Tag, Skeleton, Empty } from "@douyinfe/semi-ui";

const { Title, Text, Paragraph } = Typography;

const truncateText = (text: string, maxLength: number = 200) => {
  if (!text) return "N/A";
  return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text;
};

export interface TemplateDetailCardProps {
  template?: AgentTemplate | null;
  isDefault?: boolean;
  className?: string;
  isLoading?: boolean;
}

const TemplateDetailCardComponent = ({
  template,
  isDefault = false,
  className,
  isLoading = false,
}: TemplateDetailCardProps) => {
  if (isLoading) {
    return (
      <Card className={className}>
        <Skeleton.Title style={{ marginBottom: 16 }} />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton.Paragraph key={i} rows={1} />
          ))}
        </div>
      </Card>
    );
  }

  if (!template) {
    return (
      <Card className={`${className || ""} !border-dashed`}>
        <div className="flex items-center gap-2 mb-4">
          <LayoutTemplate className="h-5 w-5 text-gray-400" />
          <Title heading={5} className="!mb-0">Template</Title>
        </div>
        <Empty
          image={<LayoutTemplate className="h-10 w-10 text-gray-300" />}
          title="No template assigned"
          description="Create or assign a template to configure agent behavior"
        />
      </Card>
    );
  }

  const modelsList = [
    { label: "ASR Model", value: template.ASR },
    { label: "LLM Model", value: template.LLM },
    { label: "vLLM Model", value: template.VLLM },
    { label: "TTS Model", value: template.TTS },
    { label: "Memory Model", value: template.Memory },
    { label: "Intent Model", value: template.Intent },
    { label: "Summary Memory", value: template.summary_memory },
  ].filter((m) => m.value);

  return (
    <Card
      className={className}
      title={
        <div className="flex items-center gap-2">
          <LayoutTemplate className="h-5 w-5 text-blue-500" />
          <Title heading={5} className="!mb-0">Template Configuration</Title>
        </div>
      }
    >
      <Text type="tertiary" className="block mb-4">
        AI and language settings for this agent
      </Text>

      <div className="space-y-4">
        {/* Template Name */}
        <div>
          <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold block mb-1">
            Template Name
          </Text>
          <Text strong>{template.name || "—"}</Text>
          {isDefault && (
            <Tag color="green" size="small" className="ml-2">Default</Tag>
          )}
        </div>

        {/* Model Configuration */}
        {modelsList.length > 0 && (
          <div className="pt-3 border-t border-gray-100 dark:border-gray-800">
            <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold block mb-2">
              Model Configuration
            </Text>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {modelsList.map(({ label, value }) => (
                <Card
                  key={label}
                  className="!bg-gray-50 dark:!bg-gray-800/50"
                  bodyStyle={{ padding: 10 }}
                >
                  <Text type="tertiary" size="small" className="uppercase tracking-wide block mb-0.5">
                    {label}
                  </Text>
                  <code className="text-xs font-mono">{value || "—"}</code>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Prompt Preview */}
        {template.prompt && (
          <div className="pt-3 border-t border-gray-100 dark:border-gray-800">
            <Text type="tertiary" size="small" className="uppercase tracking-wide font-semibold block mb-2">
              System Prompt
            </Text>
            <Card
              className="!bg-gray-50 dark:!bg-gray-800/50"
              bodyStyle={{ padding: 12, maxHeight: 120, overflow: "auto" }}
            >
              <Paragraph className="text-sm whitespace-pre-wrap !mb-0">
                {truncateText(template.prompt, 300)}
              </Paragraph>
            </Card>
          </div>
        )}
      </div>
    </Card>
  );
};

export const TemplateDetailCard = memo(TemplateDetailCardComponent);
