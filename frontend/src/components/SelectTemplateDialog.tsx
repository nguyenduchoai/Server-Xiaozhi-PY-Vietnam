/**
 * SelectTemplateDialog - Semi Design implementation
 */

import { useState } from "react";
import { LayoutTemplate, Globe } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useTemplateList } from "@/queries/template-queries";
import type { Template } from "@/types";
import { Modal, Input, Button, Tag, Skeleton, Typography, Checkbox, Empty, Card } from "@douyinfe/semi-ui";
import { IconSearch, IconTick } from "@douyinfe/semi-icons";

const { Title, Text, Paragraph } = Typography;

export interface SelectTemplateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (templateId: string, setActive: boolean) => Promise<void>;
  isLoading?: boolean;
  excludeTemplateIds?: string[];
}

export function SelectTemplateDialog({
  open,
  onOpenChange,
  onSelect,
  isLoading = false,
  excludeTemplateIds = [],
}: SelectTemplateDialogProps) {
  const { t } = useTranslation("agents");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [setAsActive, setSetAsActive] = useState(true);

  const { data, isLoading: isLoadingTemplates } = useTemplateList({
    page: 1,
    page_size: 50,
    include_public: true,
  });

  const templates = data?.data ?? [];

  const filteredTemplates = templates.filter((template) => {
    const isExcluded = excludeTemplateIds.includes(template.id);
    if (isExcluded) return false;

    if (!searchQuery) return true;

    const query = searchQuery.toLowerCase();
    return (
      template.name.toLowerCase().includes(query) ||
      template.prompt?.toLowerCase().includes(query)
    );
  });

  const handleSelect = async () => {
    if (!selectedTemplateId) return;

    try {
      await onSelect(selectedTemplateId, setAsActive);
      handleClose();
    } catch (error) {
      console.error("Select template error:", error);
    }
  };

  const handleClose = () => {
    setSearchQuery("");
    setSelectedTemplateId(null);
    setSetAsActive(true);
    onOpenChange(false);
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <LayoutTemplate className="h-5 w-5 text-blue-500" />
          <Title heading={5} className="!mb-0">{t("select_template")}</Title>
        </div>
      }
      visible={open}
      onCancel={handleClose}
      footer={
        <div className="flex justify-end gap-2">
          <Button onClick={handleClose} disabled={isLoading}>
            {t("common:cancel")}
          </Button>
          <Button
            theme="solid"
            type="primary"
            onClick={handleSelect}
            loading={isLoading}
            disabled={!selectedTemplateId || isLoading}
          >
            {t("add_template")}
          </Button>
        </div>
      }
      width={540}
    >
      <Text type="tertiary" className="block mb-4">{t("select_template_desc")}</Text>

      <div className="space-y-4">
        {/* Search Input */}
        <Input
          prefix={<IconSearch />}
          placeholder={t("search_templates")}
          value={searchQuery}
          onChange={setSearchQuery}
        />

        {/* Templates List */}
        <div className="h-[300px] overflow-y-auto pr-2">
          {isLoadingTemplates ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton.Paragraph key={i} rows={2} />
              ))}
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <Empty
                image={<LayoutTemplate className="h-10 w-10 text-gray-300" />}
                title={searchQuery ? t("no_templates_found") : t("no_available_templates")}
              />
            </div>
          ) : (
            <div className="space-y-2">
              {filteredTemplates.map((template) => (
                <TemplateItem
                  key={template.id}
                  template={template}
                  isSelected={selectedTemplateId === template.id}
                  onSelect={() => setSelectedTemplateId(template.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Set as Active Checkbox */}
        {selectedTemplateId && (
          <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
            <Checkbox
              checked={setAsActive}
              onChange={(e) => setSetAsActive(e.target.checked || false)}
            >
              {t("set_as_active_template")}
            </Checkbox>
          </div>
        )}
      </div>
    </Modal>
  );
}

interface TemplateItemProps {
  template: Template;
  isSelected: boolean;
  onSelect: () => void;
}

function TemplateItem({ template, isSelected, onSelect }: TemplateItemProps) {
  const { t } = useTranslation("templates");

  const modelsList = [
    { label: "ASR", value: template.ASR?.name },
    { label: "LLM", value: template.LLM?.name },
    { label: "TTS", value: template.TTS?.name },
  ].filter((item) => item.value);

  return (
    <div onClick={onSelect} className="cursor-pointer">
      <Card
        className={`transition-all ${isSelected
          ? "!border-blue-500 !bg-blue-50 dark:!bg-blue-900/20"
          : "hover:!border-blue-300 hover:!bg-gray-50 dark:hover:!bg-gray-800"
          }`}
        bodyStyle={{ padding: 12 }}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Text strong className="truncate">{template.name}</Text>
              {template.is_public && (
                <Tag size="small" color="blue">
                  <Globe className="h-3 w-3 mr-1" />
                  {t("public")}
                </Tag>
              )}
            </div>
            {template.prompt && (
              <Paragraph className="text-xs !mb-0 mt-1 line-clamp-1" type="tertiary">
                {template.prompt}
              </Paragraph>
            )}
            {modelsList.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {modelsList.map((model) => (
                  <Tag key={model.label} size="small" color="grey">
                    {model.label}: {model.value}
                  </Tag>
                ))}
              </div>
            )}
          </div>
          {isSelected && (
            <div className="flex-shrink-0">
              <IconTick className="text-blue-500" size="large" />
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
