/**
 * TemplatesList - Semi Design implementation
 * Collapsible list of templates with actions
 */

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Card, Tag, Button, Dropdown, Typography, Empty } from "@douyinfe/semi-ui";
import { IconMore, IconEyeOpened, IconDelete, IconStar } from "@douyinfe/semi-icons";
import type { AgentTemplate, AgentTemplateDetail } from "@/types";

const { Text, Paragraph } = Typography;

interface TemplatesListProps {
  templates: (AgentTemplate | AgentTemplateDetail)[];
  activeTemplateId?: string | null;
  onDelete?: (templateId: string) => void;
  onSetDefault?: (templateId: string) => void;
}

export const TemplatesList = ({
  templates,
  activeTemplateId,
  onDelete,
  onSetDefault,
}: TemplatesListProps) => {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const { t } = useTranslation("agents");
  const navigate = useNavigate();

  const toggleExpanded = (templateId: string) => {
    const newExpanded = new Set(expandedIds);
    if (newExpanded.has(templateId)) {
      newExpanded.delete(templateId);
    } else {
      newExpanded.add(templateId);
    }
    setExpandedIds(newExpanded);
  };

  if (!templates || templates.length === 0) {
    return (
      <Card className="!border-dashed" bodyStyle={{ padding: 24 }}>
        <Empty title={t("no_templates")} />
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {templates.map((template) => {
        const isExpanded = expandedIds.has(template.id);
        const isDefault = activeTemplateId === template.id;

        return (
          <Card key={template.id} bodyStyle={{ padding: 0 }}>
            {/* Header */}
            <div
              className="flex items-center hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
              onClick={() => toggleExpanded(template.id)}
            >
              <div className="flex-1 px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  )}
                  <Text strong>{template.name}</Text>
                  {isDefault && (
                    <Tag color="blue" size="small">{t("template_default")}</Tag>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-1 mr-2" onClick={(e) => e.stopPropagation()}>
                {onSetDefault && !isDefault && (
                  <Button
                    icon={<IconStar />}
                    theme="borderless"
                    type="tertiary"
                    size="small"
                    onClick={() => onSetDefault(template.id)}
                    title={t("set_default")}
                  />
                )}

                <Dropdown
                  trigger="click"
                  position="bottomRight"
                  clickToHide
                  render={
                    <Dropdown.Menu>
                      <Dropdown.Item onClick={() => navigate(`/templates/${template.id}`)}>
                        <IconEyeOpened className="mr-2" />
                        {t("view_detail")}
                      </Dropdown.Item>
                      {onDelete && (
                        <Dropdown.Item type="danger" onClick={() => onDelete(template.id)}>
                          <IconDelete className="mr-2" />
                          {t("delete")}
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
                  />
                </Dropdown>
              </div>
            </div>

            {/* Content */}
            {isExpanded && (
              <div className="border-t border-gray-100 dark:border-gray-800 px-4 py-3 space-y-3 bg-gray-50 dark:bg-gray-900/30">
                {/* Template Details Grid */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {template.ASR && (
                    <div>
                      <Text type="tertiary" size="small" className="block">ASR</Text>
                      <Text>{typeof template.ASR === "string" ? template.ASR : template.ASR.name}</Text>
                    </div>
                  )}
                  {template.TTS && (
                    <div>
                      <Text type="tertiary" size="small" className="block">TTS</Text>
                      <Text>{typeof template.TTS === "string" ? template.TTS : template.TTS.name}</Text>
                    </div>
                  )}
                  {template.LLM && (
                    <div>
                      <Text type="tertiary" size="small" className="block">LLM</Text>
                      <Text>{typeof template.LLM === "string" ? template.LLM : template.LLM.name}</Text>
                    </div>
                  )}
                  {template.VLLM && (
                    <div>
                      <Text type="tertiary" size="small" className="block">VLLM</Text>
                      <Text>{typeof template.VLLM === "string" ? template.VLLM : template.VLLM.name}</Text>
                    </div>
                  )}
                  {template.Memory && (
                    <div>
                      <Text type="tertiary" size="small" className="block">Memory</Text>
                      <Text>{typeof template.Memory === "string" ? template.Memory : template.Memory.name}</Text>
                    </div>
                  )}
                </div>

                {/* Prompt Section */}
                <div className="border-t border-gray-100 dark:border-gray-800 pt-3">
                  <Text type="tertiary" size="small" className="block mb-1">{t("prompt")}</Text>
                  <Card className="!bg-white dark:!bg-gray-800" bodyStyle={{ padding: 8 }}>
                    <Paragraph className="text-sm !mb-0 break-words">
                      {template.prompt}
                    </Paragraph>
                  </Card>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-3 text-xs border-t border-gray-100 dark:border-gray-800 pt-3">
                  <div>
                    <Text type="tertiary" size="small" className="block">{t("template_created")}</Text>
                    <Text size="small">{new Date(template.created_at).toLocaleDateString()}</Text>
                  </div>
                  <div>
                    <Text type="tertiary" size="small" className="block">{t("template_updated")}</Text>
                    <Text size="small">{new Date(template.updated_at).toLocaleDateString()}</Text>
                  </div>
                </div>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
};
