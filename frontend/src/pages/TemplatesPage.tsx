
"use client";

import { useState, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { IconPlus, IconFile, IconGlobe } from "@douyinfe/semi-icons";
import {
  Button,
  Skeleton,
  Banner,
  Empty,
  Pagination,
  Typography,
  Row,
  Col,
  Switch,
  Space
} from "@douyinfe/semi-ui";

import type { Template } from "@types";
import {
  useTemplateList,
  useCreateTemplate,
  useUpdateTemplate,
} from "@/queries/template-queries";
import { useProviderModules } from "@/hooks";
import { PageHead } from "@/components/PageHead";
import { TemplateCard } from "@/components/TemplateCard";
import { CreateTemplateDialog } from "@/components/CreateTemplateDialog";

const { Title, Text } = Typography;

const DEFAULT_PAGE_SIZE = 12;

export const TemplatesPage = () => {
  const { t } = useTranslation(["templates", "common"]);
  const [searchParams, setSearchParams] = useSearchParams();
  const { modules, isLoading: modulesLoading } = useProviderModules(true);

  // URL state
  const page = useMemo(() => {
    const p = searchParams.get("page");
    return p ? parseInt(p, 10) : 1;
  }, [searchParams]);

  const includePublic = useMemo(() => {
    return searchParams.get("include_public") === "true";
  }, [searchParams]);

  // Local state
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(
    null
  );

  // Queries & Mutations
  const { data, isLoading, error, refetch } = useTemplateList({
    page,
    page_size: DEFAULT_PAGE_SIZE,
    include_public: includePublic,
  });

  const { mutateAsync: createTemplate, isPending: isCreating } =
    useCreateTemplate();
  const { mutateAsync: updateTemplate, isPending: isUpdating } =
    useUpdateTemplate();

  // Handlers
  const handleIncludePublicChange = useCallback(
    (checked: boolean) => {
      const params: Record<string, string> = { page: "1" };
      if (checked) {
        params.include_public = "true";
      }
      setSearchParams(params);
    },
    [setSearchParams]
  );

  const handlePageChange = useCallback(
    (newPage: number) => {
      const params: Record<string, string> = { page: String(newPage) };
      if (includePublic) {
        params.include_public = "true";
      }
      setSearchParams(params);
    },
    [setSearchParams, includePublic]
  );

  const handleCreate = useCallback(() => {
    setSelectedTemplate(null);
    setIsDialogOpen(true);
  }, []);

  const handleEdit = useCallback((template: Template) => {
    setSelectedTemplate(template);
    setIsDialogOpen(true);
  }, []);

  const handleSubmit = async (formData: any) => {
    if (selectedTemplate) {
      // Update
      await updateTemplate({
        templateId: selectedTemplate.id,
        payload: {
          name: formData.name,
          prompt: formData.prompt,
          ASR: formData.ASR || null,
          LLM: formData.LLM || null,
          VLLM: formData.VLLM || null,
          TTS: formData.TTS || null,
          Memory: formData.Memory || null,
          Intent: formData.Intent || null,
          summary_memory: formData.summary_memory || null,
          tts_voice: formData.tts_voice || null
        },
      });
    } else {
      // Create
      await createTemplate({
        name: formData.name,
        prompt: formData.prompt,
        ASR: formData.ASR || null,
        LLM: formData.LLM || null,
        VLLM: formData.VLLM || null,
        TTS: formData.TTS || null,
        Memory: formData.Memory || null,
        Intent: formData.Intent || null,
        summary_memory: formData.summary_memory || null,
        tts_voice: formData.tts_voice || null
      });
    }
  };

  // Convert Template to AgentTemplateDetail format for dialog compatibility
  const templateForDialog = selectedTemplate
    ? {
      id: selectedTemplate.id,
      user_id: selectedTemplate.user_id,
      name: selectedTemplate.name,
      prompt: selectedTemplate.prompt,
      ASR: selectedTemplate.ASR,
      LLM: selectedTemplate.LLM,
      VLLM: selectedTemplate.VLLM,
      TTS: selectedTemplate.TTS,
      Memory: selectedTemplate.Memory,
      Intent: selectedTemplate.Intent,
      summary_memory: selectedTemplate.summary_memory,
      created_at: selectedTemplate.created_at,
      updated_at: selectedTemplate.updated_at,
      tts_voice: selectedTemplate.tts_voice
    }
    : null;

  // Pagination
  const total = data?.total || 0;

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton.Title style={{ width: 200, marginBottom: 10 }} />
          <Skeleton.Paragraph style={{ width: 300 }} rows={1} />
        </div>
        <Row gutter={[16, 16]}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Col xs={24} sm={12} lg={8} key={i}>
              <Skeleton placeholder={<Skeleton.Image style={{ height: 200 }} />} active >
                <Skeleton.Paragraph rows={3} />
              </Skeleton>
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <Banner
          type="danger"
          description={
            <div>
              <div>{t("failed_to_load_templates")}</div>
              <Button theme="borderless" style={{ padding: 0, marginTop: 4 }} onClick={() => refetch()}>
                {t("common:retry")}
              </Button>
            </div>
          }
        />
      </div>
    );
  }

  const templates = data?.data || [];

  return (
    <>
      <PageHead
        title="templates:page.title"
        description="templates:page.description"
        translateTitle
        translateDescription
      />
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Title heading={2}>{t("templates")}</Title>
            <Text type="secondary" className="mt-1 block">
              {t("templates_description")}
            </Text>
          </div>
          <Button onClick={handleCreate} icon={<IconPlus />} theme="solid" type="primary">
            {t("create_template")}
          </Button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <Space>
            <Switch
              checked={includePublic}
              onChange={handleIncludePublicChange}
            />
            <span className="flex items-center gap-1 text-sm text-[var(--semi-color-text-0)]">
              <IconGlobe />
              {t("include_public_templates")}
            </span>
          </Space>
        </div>

        {/* Content */}
        {templates.length === 0 ? (
          <Empty
            image={<IconFile style={{ fontSize: 48, color: 'var(--semi-color-text-2)' }} />}
            title={t("no_templates")}
            description={t("no_templates_description")}
            layout="vertical"
          />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {templates.map((template) => (
                <Col xs={24} sm={12} lg={8} key={template.id}>
                  <TemplateCard
                    template={template}
                    onEdit={() => handleEdit(template)}
                  // Don't pass onDelete yet as logic wasn't in original page, but Card supports it.
                  // Can add if required.
                  />
                </Col>
              ))}
            </Row>

            {/* Pagination */}
            {total > 0 && (
              <div className="flex justify-center mt-6">
                <Pagination
                  total={total}
                  currentPage={page}
                  pageSize={DEFAULT_PAGE_SIZE}
                  onPageChange={handlePageChange}
                />
              </div>
            )}
          </>
        )}

        {/* Create/Edit Dialog */}
        <CreateTemplateDialog
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          template={templateForDialog}
          onSubmit={handleSubmit}
          isLoading={isCreating || isUpdating}
          modules={{
            ASR: modules?.ASR?.map((m) => ({
              reference: m.reference,
              id: m.id,
              name: m.name,
              type: m.type,
              source: m.source,
            })),
            TTS: modules?.TTS?.map((m) => ({
              reference: m.reference,
              id: m.id,
              name: m.name,
              type: m.type,
              source: m.source,
            })),
            LLM: modules?.LLM?.map((m) => ({
              reference: m.reference,
              id: m.id,
              name: m.name,
              type: m.type,
              source: m.source,
            })),
            VLLM: modules?.VLLM?.map((m) => ({
              reference: m.reference,
              id: m.id,
              name: m.name,
              type: m.type,
              source: m.source,
            })),
            Memory: modules?.Memory?.map((m) => ({
              reference: m.reference,
              id: m.id,
              name: m.name,
              type: m.type,
              source: m.source,
            })),
            Intent: modules?.Intent?.map((m) => ({
              reference: m.reference,
              id: m.id,
              name: m.name,
              type: m.type,
              source: m.source,
            })),
          }}
          modulesLoading={modulesLoading}
        />
      </div>
    </>
  );
};
