"use client";

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { IconAlertTriangle, IconPlus, IconDelete } from "@douyinfe/semi-icons";
import { useTranslation } from "react-i18next";
import {
  Button,
  Card,
  Typography,
  Tag,
  Skeleton,
  Empty,
  Modal,
  Banner,
  List as SemiList
} from "@douyinfe/semi-ui";
import { Bot, AlertCircle, Database } from "lucide-react";

import {
  useTemplateDetail,
  useDeleteTemplate,
  useTemplateAgents,
  useAssignTemplate,
  useUnassignTemplate,
} from "@/queries/template-queries";
import {
  useKnowledgeBases,
  type KnowledgeBase,
} from "@/queries/knowledge-bases-queries";
import {
  TemplateDetailHeader,
  SelectAgentDialog,
  PageHead,
} from "@/components";
import apiClient from "@/config/axios-instance";

const { Text } = Typography;

export const TemplateDetailPage = () => {
  const { templateId } = useParams<{ templateId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("templates");

  const [isSelectAgentDialogOpen, setIsSelectAgentDialogOpen] = useState(false);
  const [isSelectKBModalOpen, setIsSelectKBModalOpen] = useState(false);

  const { mutateAsync: deleteTemplateMutation, isPending: isDeleting } =
    useDeleteTemplate();
  const { mutateAsync: assignTemplate, isPending: isAssigning } =
    useAssignTemplate();
  const { mutateAsync: unassignTemplate } =
    useUnassignTemplate();

  // Fetch knowledge bases for display
  const { data: kbData, isLoading: kbLoading } = useKnowledgeBases();

  if (!templateId) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Empty
          image={<IconAlertTriangle style={{ fontSize: 48, color: 'var(--semi-color-danger)' }} />}
          title={t("invalid_template_id")}
          description={t("template_id_missing")}
        >
          <Button onClick={() => navigate("/templates")} theme="solid" type="tertiary">
            {t("back_to_templates")}
          </Button>
        </Empty>
      </div>
    );
  }

  const {
    data: template,
    isLoading,
    error,
    refetch,
  } = useTemplateDetail(templateId);
  const { data: agentsData, isLoading: isLoadingAgents } =
    useTemplateAgents(templateId);

  const agents = agentsData?.data ?? [];

  // Navigate to edit page instead of popup
  const handleEdit = () => {
    navigate(`/templates/${templateId}/edit`);
  };

  const handleDeleteTemplate = () => {
    Modal.confirm({
      title: t("delete_template_confirm"),
      content: t("delete_template_warning"),
      okText: t("delete"),
      okType: 'danger',
      cancelText: t("common:cancel"),
      onOk: async () => {
        try {
          await deleteTemplateMutation(templateId);
          navigate("/templates");
        } catch (error) {
          console.error("Delete template error:", error);
        }
      }
    });
  };

  const handleAddAgent = () => {
    setIsSelectAgentDialogOpen(true);
  };

  const handleSelectAgent = async (agentId: string, setActive: boolean) => {
    await assignTemplate({
      templateId,
      agentId,
      setActive,
    });
  };

  const handleRemoveAgent = (agentId: string) => {
    Modal.confirm({
      title: t("remove_agent_confirm"),
      content: t("remove_agent_warning"),
      okText: t("remove"),
      okType: 'danger',
      cancelText: t("common:cancel"),
      onOk: async () => {
        try {
          await unassignTemplate({
            templateId,
            agentId,
          });
        } catch (error) {
          console.error("Remove agent error:", error);
        }
      }
    });
  };

  // Add KB to template
  const handleAddKB = async (kbId: string) => {
    try {
      const currentIds = (template as any).knowledge_base_ids || [];
      await apiClient.put(`/templates/${templateId}`, {
        knowledge_base_ids: [...currentIds, kbId]
      });
      refetch();
      setIsSelectKBModalOpen(false);
    } catch (error) {
      console.error("Add KB error:", error);
    }
  };

  // Remove KB from template
  const handleRemoveKB = async (kbId: string) => {
    try {
      const currentIds = (template as any).knowledge_base_ids || [];
      await apiClient.put(`/templates/${templateId}`, {
        knowledge_base_ids: currentIds.filter((id: string) => id !== kbId)
      });
      refetch();
    } catch (error) {
      console.error("Remove KB error:", error);
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex-1">
            <Skeleton.Title className="mb-2 w-64" />
            <Skeleton.Paragraph className="w-24" />
          </div>
          <Skeleton.Button />
        </div>
        <Skeleton.Image className="h-64 mb-4" />
        <Skeleton.Image className="h-48" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Banner
          type="danger"
          description={
            <div className="flex items-center justify-between">
              <span>{t("templates:error_loading")}</span>
              <Button theme="borderless" type="primary" onClick={() => refetch()}>
                {t("common:retry")}
              </Button>
            </div>
          }
          icon={<AlertCircle />}
        />
      </div>
    );
  }

  if (!template) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Empty
          image={<IconAlertTriangle style={{ fontSize: 48, color: 'var(--semi-color-text-2)' }} />}
          title={t("template_not_found")}
          description={t("template_not_found_desc")}
        />
      </div>
    );
  }

  // Store template name in sessionStorage for breadcrumb display
  if (template?.name) {
    sessionStorage.setItem("currentTemplateName", template.name);
  }

  const modelsList = [
    { label: "ASR", value: template.ASR?.name },
    { label: "LLM", value: template.LLM?.name },
    { label: "TTS", value: template.TTS?.name },
    { label: "VLLM", value: template.VLLM?.name },
    { label: "Memory", value: template.Memory?.name },
    { label: "Intent", value: template.Intent?.name },
  ].filter((item) => item.value);

  // Get ONLY linked items (not all)
  const linkedKbIds = (template as any).knowledge_base_ids || [];
  const linkedKbs = kbData?.items?.filter((kb: KnowledgeBase) => linkedKbIds.includes(kb.id)) || [];

  const availableKbs = kbData?.items?.filter((kb: KnowledgeBase) => !linkedKbIds.includes(kb.id)) || [];

  return (
    <>
      <PageHead
        title={template?.name || "Template Details"}
        description="templates:page.detail_description"
        translateDescription
      />
      <div className="p-6 space-y-4">
        {/* Header with Actions */}
        <TemplateDetailHeader
          templateId={template.id}
          templateName={template.name}
          isPublic={template.is_public}
          avatarUrl={template.avatar_url}
          onEdit={handleEdit}
          onDelete={handleDeleteTemplate}
          onAvatarChange={() => refetch()}
          isDeleting={isDeleting}
        />

        {/* Template Info Card */}
        <Card
          title={t("template_info")}
          headerExtraContent={<Text type="tertiary">{t("template_info_desc")}</Text>}
        >
          <div className="space-y-4">
            {/* Prompt */}
            <div className="space-y-1">
              <Text strong style={{ textTransform: 'uppercase', fontSize: 12, color: 'var(--semi-color-text-2)' }}>
                {t("prompt")}
              </Text>
              <div className="bg-gray-50 p-3 rounded-lg whitespace-pre-wrap text-sm">
                {template.prompt || "—"}
              </div>
            </div>

            {/* Models */}
            {modelsList.length > 0 && (
              <div className="space-y-2">
                <Text strong style={{ textTransform: 'uppercase', fontSize: 12, color: 'var(--semi-color-text-2)' }}>
                  {t("models")}
                </Text>
                <div className="flex flex-wrap gap-2">
                  {modelsList.map((model) => (
                    <Tag key={model.label} color="blue" type="light">
                      <span className="font-semibold mr-1">{model.label}:</span> {model.value}
                    </Tag>
                  ))}
                </div>
              </div>
            )}

            {/* Config */}
            <div className="grid grid-cols-2 gap-4 pt-2 border-t mt-4">
              <div className="space-y-1">
                <Text strong style={{ textTransform: 'uppercase', fontSize: 12, color: 'var(--semi-color-text-2)' }}>
                  {t("created_at")}
                </Text>
                <Text>
                  {new Date(template.created_at).toLocaleDateString()}
                </Text>
              </div>
              <div className="space-y-1">
                <Text strong style={{ textTransform: 'uppercase', fontSize: 12, color: 'var(--semi-color-text-2)' }}>
                  {t("updated_at")}
                </Text>
                <Text>
                  {new Date(template.updated_at).toLocaleDateString()}
                </Text>
              </div>
            </div>

            {/* Memory Scope Selector */}
            <div className="pt-3 border-t mt-3 space-y-2">
              <Text strong style={{ textTransform: 'uppercase', fontSize: 12, color: 'var(--semi-color-text-2)' }}>
                🧠 Memory Scope
              </Text>
              <Text type="tertiary" size="small" className="block">
                Cách quản lý bộ nhớ khi nhiều thiết bị dùng chung agent
              </Text>
              <div className="flex flex-wrap gap-2 mt-1">
                {[
                  { value: 'agent_shared', label: 'Chia sẻ', desc: 'Tất cả thiết bị chung bộ nhớ', color: 'blue' },
                  { value: 'device_isolated', label: 'Tách biệt', desc: 'Mỗi thiết bị riêng biệt', color: 'orange' },
                  { value: 'hybrid', label: 'Lai', desc: 'Chung KB + riêng hội thoại', color: 'green' },
                ].map((opt) => {
                  const isActive = ((template as any).memory_scope || 'agent_shared') === opt.value;
                  return (
                    <button
                      key={opt.value}
                      onClick={async () => {
                        try {
                          await apiClient.put(`/templates/${templateId}`, { memory_scope: opt.value });
                          refetch();
                        } catch (e) { console.error(e); }
                      }}
                      className={`px-3 py-2 rounded-lg border text-left transition-all ${
                        isActive
                          ? 'border-blue-500 bg-blue-50 shadow-sm'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      style={{ minWidth: 120 }}
                    >
                      <Text strong className="block" style={{ fontSize: 13 }}>{opt.label}</Text>
                      <Text type="tertiary" size="small" className="block">{opt.desc}</Text>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </Card>

        {/* Knowledge Base Section - Popup Add Pattern */}
        <Card
          title={
            <div className="flex items-center gap-2">
              <Database size={18} />
              <span>{t("knowledge_bases", "Kho Tri Thức")}</span>
              <Tag color="blue" size="small">{linkedKbs.length}</Tag>
            </div>
          }
          headerExtraContent={
            <Button
              icon={<IconPlus />}
              size="small"
              theme="light"
              onClick={() => setIsSelectKBModalOpen(true)}
            >
              {t("add", "Thêm")}
            </Button>
          }
        >
          {kbLoading ? (
            <Skeleton.Paragraph rows={2} />
          ) : linkedKbs.length === 0 ? (
            <Empty
              image={<Database size={40} className="text-gray-300" />}
              title={t("no_knowledge_bases_linked", "Chưa liên kết kho tri thức")}
              description={t("no_knowledge_bases_linked_desc", "Bấm Thêm để chọn kho tri thức")}
            />
          ) : (
            <div className="space-y-2">
              {linkedKbs.map((kb: KnowledgeBase) => (
                <div
                  key={kb.id}
                  className="p-3 rounded-lg border border-gray-200 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <Database size={16} className="text-blue-500" />
                    <div>
                      <Text strong>{kb.name}</Text>
                      {kb.description && (
                        <Text type="tertiary" size="small" className="block">
                          {kb.description}
                        </Text>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Tag color="blue" size="small">
                      {kb.entry_count} entries
                    </Tag>
                    <Button
                      icon={<IconDelete />}
                      size="small"
                      type="danger"
                      theme="borderless"
                      onClick={() => handleRemoveKB(kb.id)}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Agents Using Template */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">
              {t("agents_using_template")}
            </h3>
            <Button
              icon={<IconPlus />}
              theme="light"
              onClick={handleAddAgent}
            >
              {t("add_agent")}
            </Button>
          </div>

          {isLoadingAgents ? (
            <div className="space-y-2">
              <Skeleton.Image className="h-16 mb-2" />
              <Skeleton.Image className="h-16" />
            </div>
          ) : agents.length > 0 ? (
            <div className="space-y-2">
              {agents.map((agent) => (
                <Card
                  key={agent.id}
                  bodyStyle={{ padding: 12 }}
                  className="hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Bot className="h-5 w-5 text-gray-500" />
                      <div>
                        <Text strong style={{ display: 'block' }}>{agent.agent_name}</Text>
                        {agent.description && (
                          <Text type="tertiary" size="small" ellipsis={{ showTooltip: true }} style={{ width: 300 }}>
                            {agent.description}
                          </Text>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Tag color={agent.status === "enabled" ? "green" : "grey"}>
                        {agent.status === "enabled" ? t("agents:enabled") : t("common:disabled")}
                      </Tag>
                      {agent.active_template_id === templateId && (
                        <Tag color="blue">{t("common:default")}</Tag>
                      )}
                      <Button
                        icon={<IconDelete />}
                        type="danger"
                        theme="borderless"
                        onClick={() => handleRemoveAgent(agent.id)}
                      />
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 p-6 flex items-center justify-center">
              <div className="flex items-center gap-3 text-gray-500">
                <Bot className="h-5 w-5" />
                <span className="text-sm">{t("no_agents_using_template")}</span>
              </div>
            </div>
          )}
        </div>

        {/* Select Agent Dialog */}
        <SelectAgentDialog
          open={isSelectAgentDialogOpen}
          onOpenChange={setIsSelectAgentDialogOpen}
          onSelect={handleSelectAgent}
          isLoading={isAssigning}
          excludeAgentIds={agents.map((a) => a.id)}
        />

        {/* Select KB Modal */}
        <Modal
          title={
            <div className="flex items-center gap-2">
              <Database size={20} />
              <span>Thêm Kho Tri Thức</span>
            </div>
          }
          visible={isSelectKBModalOpen}
          onCancel={() => setIsSelectKBModalOpen(false)}
          footer={null}
          width={500}
        >
          {availableKbs.length === 0 ? (
            <Empty
              title="Không có kho tri thức nào"
              description="Tất cả kho tri thức đã được thêm hoặc chưa có kho tri thức nào"
            />
          ) : (
            <SemiList
              dataSource={availableKbs}
              renderItem={(kb: KnowledgeBase) => (
                <SemiList.Item
                  main={
                    <div>
                      <Text strong>{kb.name}</Text>
                      {kb.description && (
                        <Text type="tertiary" size="small" className="block">{kb.description}</Text>
                      )}
                    </div>
                  }
                  extra={
                    <Button
                      icon={<IconPlus />}
                      theme="solid"
                      size="small"
                      onClick={() => handleAddKB(kb.id)}
                    >
                      Thêm
                    </Button>
                  }
                />
              )}
            />
          )}
        </Modal>


      </div>
    </>
  );
};
