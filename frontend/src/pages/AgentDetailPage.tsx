"use client";

import { useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { IconAlertTriangle } from "@douyinfe/semi-icons";
import { useTranslation } from "react-i18next";
import {
  Button,
  Skeleton,
  Empty,
  Banner,
  Modal
} from "@douyinfe/semi-ui";

import {
  useAgentDetail,
  useUpdateAgent,
  useBindAgentDevice,
  useActivateAgentTemplate,
  useDeleteAgent,
  useBindAgentDeviceById,
} from "@/queries/agent-queries";
import {
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
  useAssignTemplate,
  useUnassignTemplate,
} from "@/queries/template-queries";
import {
  useAgentReminders,
  useCreateReminder,
  useUpdateReminder,
  useDeleteReminder,
} from "@/queries/reminder-queries";
import {
  useAgentMcp,
  useAvailableMcpServers,
  useUpdateAgentMcp,
} from "@/queries/agent-mcp-queries";
import { useProviderModules } from "@/hooks";
import {
  AgentDetailHeader,
  PageHead,
  AgentDialog,
  BindDeviceDialog,
  CreateTemplateDialog,
  ReminderDialog,
  McpSelectionDialog,
  WebhookApiDialog,
  AgentDetailTabs,
} from "@/components";
import type { BindDeviceFormValues } from "@/components/BindDeviceDialog";
import type { AgentTemplateDetail, ReminderRead, ReminderStatus } from "@types";
import type {
  TemplatePayload,
  UpdateTemplatePayload,
  CreateReminderPayload,
  UpdateReminderPayload,
} from "@types";

export const AgentDetailPage = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("agents");
  const { modules, isLoading: modulesLoading } = useProviderModules(true);

  const [isUpdateDialogOpen, setIsUpdateDialogOpen] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [isBindDeviceDialogOpen, setIsBindDeviceDialogOpen] = useState(false);
  const [isCreateTemplateDialogOpen, setIsCreateTemplateDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<AgentTemplateDetail | null>(null);
  const [isReminderDialogOpen, setIsReminderDialogOpen] = useState(false);
  const [editingReminder, setEditingReminder] = useState<ReminderRead | null>(null);
  const [isMcpSelectionDialogOpen, setIsMcpSelectionDialogOpen] = useState(false);
  const [isWebhookApiDialogOpen, setIsWebhookApiDialogOpen] = useState(false);

  const { mutateAsync: updateAgent, isPending: isUpdating } = useUpdateAgent();
  const { mutateAsync: bindDevice, isPending: isBindingDevice } =
    useBindAgentDevice(agentId || "");

  const { mutateAsync: bindDeviceById, isPending: isBindingDeviceById } =
    useBindAgentDeviceById(agentId || "");

  // MCP Selection queries
  const { data: agentMcpData, refetch: refetchAgentMcp } = useAgentMcp(
    agentId || "",
    !!agentId
  );
  const { data: availableMcpServersData } = useAvailableMcpServers(
    agentId || "",
    "all",
    !!agentId
  );
  const { mutateAsync: updateAgentMcp, isPending: isUpdatingMcp } =
    useUpdateAgentMcp();

  // Template mutations
  const { mutateAsync: createTemplate, isPending: isCreatingTemplate } =
    useCreateTemplate();
  const { mutateAsync: updateTemplateMutation, isPending: isUpdatingTemplate } =
    useUpdateTemplate();
  const { mutateAsync: deleteTemplateMutation } = useDeleteTemplate();
  const { mutateAsync: assignTemplate } = useAssignTemplate();
  const { mutateAsync: unassignTemplate } = useUnassignTemplate();
  const { mutateAsync: activateTemplate } = useActivateAgentTemplate(
    agentId || ""
  );
  const { mutateAsync: deleteAgentMutation } = useDeleteAgent();

  const [reminderStatus, setReminderStatus] = useState<ReminderStatus | undefined>(undefined);
  const reminderParams = useMemo(
    () => (reminderStatus ? { status: reminderStatus } : undefined),
    [reminderStatus]
  );
  const {
    data: reminders,
    isLoading: isLoadingReminders,
    refetch: refetchReminders,
  } = useAgentReminders(agentId || "", reminderParams);
  const { mutateAsync: createReminder, isPending: isCreatingReminder } =
    useCreateReminder();
  const { mutateAsync: updateReminderMutation, isPending: isUpdatingReminder } =
    useUpdateReminder();
  const { mutateAsync: deleteReminderMutation } = useDeleteReminder();

  // Custom Confirm Modal State
  const [confirmModalState, setConfirmModalState] = useState<{
    isOpen: boolean;
    title: string;
    content: React.ReactNode;
    onConfirm: () => Promise<void>;
    okText?: string;
    okType?: "primary" | "danger" | "warning";
  }>({
    isOpen: false,
    title: "",
    content: null,
    onConfirm: async () => { },
    okText: "OK",
    okType: "primary"
  });

  const showConfirm = (options: {
    title: string;
    content: React.ReactNode;
    onOk: () => Promise<void>;
    okText?: string;
    okType?: "primary" | "danger" | "warning";
  }) => {
    setConfirmModalState({
      isOpen: true,
      title: options.title,
      content: options.content,
      onConfirm: options.onOk,
      okText: options.okText,
      okType: options.okType
    });
  };

  if (!agentId) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Empty
          image={<IconAlertTriangle style={{ fontSize: 48, color: 'var(--semi-color-danger)' }} />}
          title={t("invalid_agent_id")}
          description={t("agent_id_missing")}
        >
          <Button onClick={() => navigate("/agents")} theme="solid" type="tertiary">
            {t("back_to_agents")}
          </Button>
        </Empty>
      </div>
    );
  }

  const { data, isLoading, error, refetch } = useAgentDetail(agentId);

  const handleEdit = () => {
    setIsUpdateDialogOpen(true);
  };

  const handleUpdateSubmit = async (formData: any) => {
    setUpdateError(null);
    try {
      await updateAgent({
        agentId,
        payload: {
          agent_name: formData.agent_name,
          description: formData.description,
          user_profile: formData.user_profile,
          status: formData.status,
          chat_history_conf: formData.chat_history_conf,
        },
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : t("agents:error_updating_agent");
      setUpdateError(errorMessage);
      throw err;
    }
  };

  const handleAddDevice = () => {
    setIsBindDeviceDialogOpen(true);
  };

  const handleBindDeviceSubmit = async (formData: BindDeviceFormValues) => {
    await bindDevice(formData);
  };

  const handleAddTemplate = () => {
    setSelectedTemplate(null);
    setIsCreateTemplateDialogOpen(true);
  };

  const handleAddReminder = () => {
    setEditingReminder(null);
    setIsReminderDialogOpen(true);
  };

  const handleTemplateSubmit = async (
    data: TemplatePayload | UpdateTemplatePayload
  ) => {
    try {
      if (selectedTemplate) {
        // Update existing template
        await updateTemplateMutation({
          templateId: selectedTemplate.id,
          payload: data as UpdateTemplatePayload,
        });
      } else {
        // Create new template and assign to agent
        const newTemplate = await createTemplate(data as TemplatePayload);
        // Assign to current agent and set as active
        if (agentId) {
          await assignTemplate({
            templateId: newTemplate.id,
            agentId,
            setActive: true,
          });
        }
      }
    } catch (error) {
      console.error("Template submit error:", error);
    }
  };

  const handleDeleteTemplate = (templateId: string) => {
    showConfirm({
      title: t("delete_template_confirm", { ns: "templates" }),
      content: t("delete_template_warning", { ns: "templates" }),
      okText: t("delete"),
      okType: 'danger',
      onOk: async () => {
        if (agentId) {
          try {
            await unassignTemplate({ templateId, agentId });
          } catch { }
        }
        await deleteTemplateMutation(templateId);
      }
    });
  };

  const handleEditReminder = (reminder: ReminderRead) => {
    setEditingReminder(reminder);
    setIsReminderDialogOpen(true);
  };

  const handleDeleteReminder = (reminderId: string) => {
    showConfirm({
      title: t("delete_reminder_confirm", "Delete Reminder"),
      content: t("delete_reminder_warning", "Are you sure?"),
      okText: t("delete"),
      okType: 'danger',
      onOk: async () => {
        if (agentId) {
          await deleteReminderMutation({ reminderId, agentId });
          await refetchReminders();
        }
      }
    });
  };

  const handleSetDefaultTemplate = async (templateId: string) => {
    try {
      await activateTemplate(templateId);
    } catch (error) {
      console.error("Set default template error:", error);
    }
  };

  const handleSubmitReminder = async (
    payload: CreateReminderPayload | UpdateReminderPayload
  ) => {
    if (!agentId) return;
    try {
      if (editingReminder) {
        await updateReminderMutation({
          reminderId: editingReminder.id,
          payload,
          agentId,
        });
      } else {
        const createPayload = payload as CreateReminderPayload;
        await createReminder({ agentId, payload: createPayload });
      }
      await refetchReminders();
      setIsReminderDialogOpen(false);
      setEditingReminder(null);
    } catch (error) {
      console.error("Reminder submit error:", error);
    }
  };

  const handleMcpSelectionSubmit = async (mode: any, servers: any[]) => {
    if (!agentId) return;
    try {
      await updateAgentMcp({
        agentId,
        payload: {
          mode,
          servers: mode === "all" ? undefined : servers,
        },
      });
      await refetchAgentMcp();
      setIsMcpSelectionDialogOpen(false);
    } catch (error) {
      console.error("MCP selection update error:", error);
      throw error;
    }
  };

  const handleDeleteAgent = () => {
    showConfirm({
      title: t("delete_agent"),
      content: t("delete_agent_confirm_desc"),
      okText: t("common:delete"),
      okType: 'danger',
      onOk: async () => {
        if (agentId) {
          await deleteAgentMutation(agentId);
          navigate("/agents");
        }
      }
    });
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
        <Skeleton.Image className="h-96" />
        <Skeleton.Image className="h-96" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Banner
          type="danger"
          title={t("error_loading")}
          description={
            <div className="flex items-center justify-between">
              <span>{error?.message || t("error_loading_description")}</span>
              <Button theme="borderless" type="primary" onClick={() => refetch()}>
                {t("retry")}
              </Button>
            </div>
          }
          icon={<IconAlertTriangle />}
        /></div>
    );
  }

  if (!data || !data.agent) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Empty
          image={<IconAlertTriangle style={{ fontSize: 48, color: 'var(--semi-color-text-2)' }} />}
          title={t("agent_not_found")}
          description={t("agent_not_found_desc")}
        />
      </div>
    );
  }

  const { agent, devices, templates } = data;

  // Store agent name in sessionStorage for breadcrumb display
  if (agent?.agent_name) {
    sessionStorage.setItem("currentAgentName", agent.agent_name);
  }

  return (
    <>
      <PageHead
        title={agent?.agent_name || t("agent_details", "Agent Details")}
        description="agents:page.detail_description"
        translateDescription
      />
      <div className="p-6 space-y-4">
        {/* Header with Actions */}
        <AgentDetailHeader
          agentId={agent.id}
          agentName={agent.agent_name}
          status={agent.status}
          avatarUrl={agent.avatar_url}
          onEdit={handleEdit}
          onDelete={handleDeleteAgent}
          onAvatarChange={() => refetch()}
        />

        {/* Tab-based Layout - Apple Style UX */}
        <AgentDetailTabs
          agent={agent}
          agentId={agentId || ''}
          devices={devices || []}
          templates={templates || []}
          isLoading={isLoading}
          onRefresh={refetch}
          onAddDevice={handleAddDevice}
          onAddTemplate={handleAddTemplate}
          onDeleteTemplate={handleDeleteTemplate}
          onSetDefaultTemplate={handleSetDefaultTemplate}
          agentMcpData={agentMcpData}
          isUpdatingMcp={isUpdatingMcp}
          onManageMcp={() => setIsMcpSelectionDialogOpen(true)}
          reminders={reminders}
          isLoadingReminders={isLoadingReminders}
          reminderStatus={reminderStatus}
          onReminderStatusChange={setReminderStatus}
          onAddReminder={handleAddReminder}
          onEditReminder={handleEditReminder}
          onDeleteReminder={handleDeleteReminder}
        />

        {/* Update Agent Dialog */}
        {agent && (
          <AgentDialog
            open={isUpdateDialogOpen}
            onOpenChange={setIsUpdateDialogOpen}
            mode="update"
            agent={agent}
            onSubmit={handleUpdateSubmit}
            isLoading={isUpdating}
            error={updateError}
            onErrorDismiss={() => setUpdateError(null)}
          />
        )}

        {/* Bind Device Dialog */}
        <BindDeviceDialog
          open={isBindDeviceDialogOpen}
          onOpenChange={setIsBindDeviceDialogOpen}
          onSubmit={handleBindDeviceSubmit}
          onBindById={async (deviceId) => {
            await bindDeviceById({ device_id: deviceId });
          }}
          isLoading={isBindingDevice || isBindingDeviceById}
        />

        {/* Create/Edit Template Dialog */}
        <CreateTemplateDialog
          open={isCreateTemplateDialogOpen}
          onOpenChange={setIsCreateTemplateDialogOpen}
          template={selectedTemplate}
          onSubmit={handleTemplateSubmit}
          isLoading={isCreatingTemplate || isUpdatingTemplate}
          modules={{
            ASR: modules?.ASR?.map((m) => ({ reference: m.reference, id: m.id, name: m.name, type: m.type, source: m.source })),
            TTS: modules?.TTS?.map((m) => ({ reference: m.reference, id: m.id, name: m.name, type: m.type, source: m.source })),
            LLM: modules?.LLM?.map((m) => ({ reference: m.reference, id: m.id, name: m.name, type: m.type, source: m.source })),
            VLLM: modules?.VLLM?.map((m) => ({ reference: m.reference, id: m.id, name: m.name, type: m.type, source: m.source })),
            Memory: modules?.Memory?.map((m) => ({ reference: m.reference, id: m.id, name: m.name, type: m.type, source: m.source })),
            Intent: modules?.Intent?.map((m) => ({ reference: m.reference, id: m.id, name: m.name, type: m.type, source: m.source })),
          }}
          modulesLoading={modulesLoading}
        />

        {/* Reminder Dialog */}
        <ReminderDialog
          open={isReminderDialogOpen}
          onOpenChange={setIsReminderDialogOpen}
          reminder={editingReminder}
          onSubmit={handleSubmitReminder}
          isLoading={isCreatingReminder || isUpdatingReminder}
        />

        {/* MCP Selection Dialog */}
        {agentId && (
          <McpSelectionDialog
            open={isMcpSelectionDialogOpen}
            onOpenChange={setIsMcpSelectionDialogOpen}
            agentId={agentId}
            agentName={agent?.agent_name}
            currentSelection={agentMcpData?.data}
            availableServers={
              Array.isArray(availableMcpServersData?.mcp_servers)
                ? availableMcpServersData.mcp_servers
                : []
            }
            onSubmit={handleMcpSelectionSubmit}
            isLoading={false}
          />
        )}

        {/* Webhook API Dialog */}
        {agentId && (
          <WebhookApiDialog
            open={isWebhookApiDialogOpen}
            onOpenChange={setIsWebhookApiDialogOpen}
            agentId={agentId}
            agentName={agent?.agent_name || ''}
          />
        )}

        {/* Custom Confirm Modal */}
        <Modal
          visible={confirmModalState.isOpen}
          title={confirmModalState.title}
          onCancel={() => setConfirmModalState((prev) => ({ ...prev, isOpen: false }))}
          onOk={async () => {
            if (confirmModalState.onConfirm) {
              await confirmModalState.onConfirm();
            }
            setConfirmModalState((prev) => ({ ...prev, isOpen: false }));
          }}
          okText={confirmModalState.okText}
          okType={confirmModalState.okType as any}
          centered
        >
          {confirmModalState.content}
        </Modal>
      </div>
    </>
  );
};
