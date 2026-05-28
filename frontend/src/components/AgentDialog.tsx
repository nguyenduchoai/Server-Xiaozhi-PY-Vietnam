import { toast } from "sonner";

import { memo, useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal, Form, TextArea, Input, Select, Typography } from '@douyinfe/semi-ui';

import type { Agent, ChatHistoryConf } from "@types";
import { CHAT_HISTORY_CONF_LABELS } from "@types";

/**
 * Agent Dialog Form Schema
 */
const createAgentSchema = z.object({
  agent_name: z
    .string()
    .min(1, "Agent name is required")
    .min(3, "Agent name must be at least 3 characters")
    .max(100, "Agent name must not exceed 100 characters"),
  description: z
    .string()
    .max(500, "Description must not exceed 500 characters"),
  user_profile: z
    .string()
    .max(1000, "User profile must not exceed 1000 characters"),
  chat_history_conf: z.number().int().min(0).max(2),
});

const updateAgentSchema = createAgentSchema.extend({
  status: z.enum(["enabled", "disabled"]),
  chat_history_conf: z.number().int().min(0).max(2),
});

type CreateAgentFormValues = z.infer<typeof createAgentSchema>;
type UpdateAgentFormValues = z.infer<typeof updateAgentSchema>;
type AgentFormValues = CreateAgentFormValues | UpdateAgentFormValues;

export type { CreateAgentFormValues, UpdateAgentFormValues };

export interface AgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "update";
  agent?: Agent | null;
  onSubmit: (data: AgentFormValues) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
  onErrorDismiss?: () => void;
}

const AgentDialogComponent = ({
  open,
  onOpenChange,
  mode,
  agent,
  onSubmit,
  isLoading = false,
  error = null,
  onErrorDismiss,
}: AgentDialogProps) => {
  const { t } = useTranslation(["agents", "common"]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isSubmittingRef = useRef(false);

  const schema = mode === "update" ? updateAgentSchema : createAgentSchema;

  const { control, handleSubmit, reset, formState: { errors } } = useForm<AgentFormValues>({
    resolver: zodResolver(schema),
    defaultValues:
      mode === "update" && agent
        ? {
          agent_name: agent.agent_name,
          description: agent.description || "",
          user_profile: agent.user_profile || "",
          chat_history_conf: (agent.chat_history_conf ?? 0) as ChatHistoryConf,
          ...(mode === "update" && { status: agent.status }),
        }
        : {
          agent_name: "",
          description: "",
          user_profile: "",
          chat_history_conf: 0,
          ...(mode === "update" && { status: "enabled" }),
        },
  });

  useEffect(() => {
    if (open) {
      if (mode === 'create') {
        reset({
          agent_name: "",
          description: "",
          user_profile: "",
          chat_history_conf: 0,
        });
      } else if (agent) {
        reset({
          agent_name: agent.agent_name,
          description: agent.description || "",
          user_profile: agent.user_profile || "",
          chat_history_conf: (agent.chat_history_conf ?? 0) as ChatHistoryConf,
          status: agent.status,
        });
      }
    }
  }, [open, mode, agent, reset]);

  const onFormSubmit = async (data: AgentFormValues) => {
    setIsSubmitting(true);
    isSubmittingRef.current = true;
    try {
      await onSubmit(data);
      reset();
      onOpenChange(false);
    } catch (e) {
      // Error handled by parent
    } finally {
      setIsSubmitting(false);
      isSubmittingRef.current = false;
    }
  };

  useEffect(() => {
    if (error) {
      toast.error(error);
      onErrorDismiss?.();
    }
  }, [error, onErrorDismiss]);


  const isCreateMode = mode === "create";
  const title = isCreateMode
    ? t("agents:create_agent")
    : t("agents:update_agent");

  return (
    <Modal
      title={title}
      visible={open}
      onCancel={() => onOpenChange(false)}
      onOk={handleSubmit(onFormSubmit)}
      confirmLoading={isLoading || isSubmitting}
      okText={isCreateMode ? t("agents:create_agent") : t("agents:update_agent")}
      cancelText={t("common:cancel")}
      size="medium"
    >
      <Form className="w-full">

        <Controller
          control={control}
          name="agent_name"
          render={({ field }) => (
            <div className="mb-4">
              <Typography.Text className="block mb-1">{t("agents:agent_name")}</Typography.Text>
              <Input
                placeholder={t("agents:agent_name")}
                value={field.value}
                onChange={field.onChange}
              />
              {errors.agent_name?.message && <Typography.Text type="danger">{errors.agent_name.message}</Typography.Text>}
            </div>
          )}
        />

        <Controller
          control={control}
          name="description"
          render={({ field }) => (
            <div className="mb-4">
              <Typography.Text className="block mb-1">{t("agents:agent_description")}</Typography.Text>
              <TextArea
                placeholder={t("agents:agent_description")}
                value={field.value}
                onChange={field.onChange}
                showClear
              />
              {errors.description?.message && <Typography.Text type="danger">{errors.description.message}</Typography.Text>}
            </div>
          )}
        />

        <Controller
          control={control}
          name="user_profile"
          render={({ field }) => (
            <div className="mb-4">
              <Typography.Text className="block mb-1">{t("agents:user_profile") || "User Profile"}</Typography.Text>
              <TextArea
                placeholder={t("agents:user_profile_placeholder") || "Enter user profile information..."}
                value={field.value}
                onChange={field.onChange}
                showClear
                autosize={{ minRows: 4, maxRows: 8 }}
              />
              {errors.user_profile?.message && <Typography.Text type="danger">{errors.user_profile.message}</Typography.Text>}
            </div>
          )}
        />

        {!isCreateMode && (
          <Controller
            control={control}
            name="status"
            render={({ field }) => (
              <div className="mb-4">
                <Typography.Text className="block mb-1">{t("agents:status")}</Typography.Text>
                <Select
                  value={field.value}
                  onChange={field.onChange}
                  style={{ width: '100%' }}
                >
                  <Select.Option value="enabled">{t("agents:enabled")}</Select.Option>
                  <Select.Option value="disabled">{t("agents:disabled")}</Select.Option>
                </Select>
              </div>
            )}
          />
        )}

        <Controller
          control={control}
          name="chat_history_conf"
          render={({ field }) => (
            <div className="mb-4">
              <Typography.Text className="block mb-1">{t("agents:chat_history_conf")}</Typography.Text>
              <Select
                value={field.value}
                onChange={(val) => field.onChange(Number(val))}
                style={{ width: '100%' }}
              >
                <Select.Option value={0}>{CHAT_HISTORY_CONF_LABELS[0]}</Select.Option>
                <Select.Option value={1}>{CHAT_HISTORY_CONF_LABELS[1]}</Select.Option>
                <Select.Option value={2}>{CHAT_HISTORY_CONF_LABELS[2]}</Select.Option>
              </Select>
              <Typography.Text type="tertiary" size="small">{t("agents:chat_history_conf_desc") || "Configure how to save chat history"}</Typography.Text>
            </div>
          )}
        />

      </Form>
    </Modal>
  );
};

export const AgentDialog = memo(AgentDialogComponent);
