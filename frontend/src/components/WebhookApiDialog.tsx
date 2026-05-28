/**
 * WebhookApiDialog - Semi Design implementation
 */

import { useState } from "react";
import { Key } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  useGetWebhookConfig,
  useCreateWebhookConfig,
  useDeleteWebhookConfig,
} from "@/queries/agent-queries";
import { Modal, Button, Input, Tag, Typography, Card, Banner, Spin } from "@douyinfe/semi-ui";
import { IconCopy, IconEyeOpened, IconEyeClosed, IconDelete } from "@douyinfe/semi-icons";

const { Title, Text } = Typography;

type WebhookApiDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId: string;
  agentName: string;
};

export function WebhookApiDialog({
  open,
  onOpenChange,
  agentId,
  agentName,
}: WebhookApiDialogProps) {
  const { t } = useTranslation(["agents", "common"]);
  const [showKey, setShowKey] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const { data: webhookConfig, isLoading: isLoadingConfig } =
    useGetWebhookConfig(agentId, open);
  const { mutateAsync: createWebhookConfig, isPending: isCreatingConfig } =
    useCreateWebhookConfig(agentId);
  const { mutateAsync: deleteWebhookConfig, isPending: isDeletingConfig } =
    useDeleteWebhookConfig(agentId);

  const apiKey = webhookConfig?.data?.api_key;

  const handleCreateKey = async () => {
    try {
      await createWebhookConfig();
      setShowKey(true);
    } catch (error) {
      console.error("Failed to create webhook config:", error);
    }
  };

  const handleDeleteKey = async () => {
    try {
      await deleteWebhookConfig();
      setShowKey(false);
      setDeleteConfirmOpen(false);
    } catch (error) {
      console.error("Failed to delete webhook config:", error);
    }
  };

  const handleCopyKey = async () => {
    if (!apiKey) return;
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  const maskKey = (key: string): string => {
    if (key.length <= 8) return key;
    return key.slice(0, 4) + "•".repeat(key.length - 8) + key.slice(-4);
  };

  return (
    <>
      <Modal
        title={
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5 text-blue-500" />
            <Title heading={5} className="!mb-0">{t("webhook_api_key", "Webhook API Key")}</Title>
          </div>
        }
        visible={open}
        onCancel={() => onOpenChange(false)}
        footer={null}
        width={480}
      >
        <Text type="tertiary" className="block mb-4">
          {t("webhook_api_description", "Quản lý API key để kích hoạt agent thông qua webhook")}
        </Text>

        <div className="space-y-4">
          {/* Agent Info */}
          <Card className="!bg-gray-50 dark:!bg-gray-800" bodyStyle={{ padding: 12 }}>
            <Text type="tertiary" size="small" className="block mb-1">
              {t("common:agent", "Agent")}
            </Text>
            <Text strong>{agentName}</Text>
          </Card>

          {/* API Key Section */}
          {isLoadingConfig ? (
            <div className="flex items-center justify-center py-8">
              <Spin />
            </div>
          ) : apiKey ? (
            <div className="space-y-3">
              <Tag color="green">{t("key_active", "Key đã kích hoạt")}</Tag>

              <div className="space-y-2">
                <Text type="tertiary" size="small" className="block">
                  {t("api_key", "API Key")}
                </Text>
                <div className="flex gap-2">
                  <Input
                    type={showKey ? "text" : "password"}
                    value={showKey ? apiKey : maskKey(apiKey)}
                    readOnly
                    className="font-mono"
                  />
                  <Button
                    icon={showKey ? <IconEyeClosed /> : <IconEyeOpened />}
                    onClick={() => setShowKey(!showKey)}
                    title={showKey ? t("hide", "Ẩn") : t("show", "Hiện")}
                  />
                  <Button
                    icon={<IconCopy />}
                    onClick={handleCopyKey}
                    title={t("copy", "Sao chép")}
                  />
                </div>
                {copied && (
                  <Text type="success" size="small">
                    {t("copied", "Đã sao chép vào clipboard")}
                  </Text>
                )}
              </div>

              {/* Webhook URL Info */}
              <Card className="!bg-gray-50 dark:!bg-gray-800" bodyStyle={{ padding: 12 }}>
                <Text type="tertiary" size="small" className="block mb-1">
                  {t("webhook_url", "Webhook URL")}
                </Text>
                <code className="text-xs break-all">
                  POST /api/v1/agents/{agentId}/webhook?token=YOUR_API_KEY
                </code>
              </Card>

              {/* Usage Info */}
              <div className="text-sm space-y-2">
                <Text strong size="small">{t("usage_instructions", "Hướng dẫn sử dụng")}</Text>
                <ul className="list-disc list-inside space-y-1 text-xs text-gray-500 dark:text-gray-400">
                  <li>{t("pass_token_param", "Truyền token qua query parameter hoặc header X-Agent-Token")}</li>
                  <li>{t("keep_key_secure", "Giữ API key an toàn và không chia sẻ công khai")}</li>
                  <li>{t("rotate_key_regularly", "Xoá và tạo key mới định kỳ để bảo mật")}</li>
                </ul>
              </div>

              <Button
                type="danger"
                theme="solid"
                block
                icon={<IconDelete />}
                onClick={() => setDeleteConfirmOpen(true)}
                loading={isDeletingConfig}
              >
                {isDeletingConfig ? t("deleting", "Đang xoá...") : t("delete_key", "Xoá API Key")}
              </Button>
            </div>
          ) : (
            <div className="space-y-4 py-2">
              <Banner
                type="warning"
                description={t("no_webhook_key", "Agent này chưa có API key. Tạo một key để bắt đầu sử dụng webhook.")}
              />

              <Button
                type="primary"
                theme="solid"
                block
                onClick={handleCreateKey}
                loading={isCreatingConfig}
              >
                {isCreatingConfig ? t("creating", "Đang tạo...") : t("create_api_key", "Tạo API Key")}
              </Button>
            </div>
          )}
        </div>
      </Modal>

      {/* Delete Confirmation Dialog */}
      <Modal
        title={t("delete_api_key_confirm", "Xoá API Key?")}
        visible={deleteConfirmOpen}
        onCancel={() => setDeleteConfirmOpen(false)}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setDeleteConfirmOpen(false)}>
              {t("common:cancel", "Hủy")}
            </Button>
            <Button
              type="danger"
              theme="solid"
              onClick={handleDeleteKey}
              loading={isDeletingConfig}
            >
              {isDeletingConfig ? t("deleting", "Đang xoá...") : t("delete", "Xoá")}
            </Button>
          </div>
        }
      >
        <Text>
          {t("delete_api_key_warning", "Webhook không còn hoạt động sau khi xoá. Hành động này không thể hoàn tác.")}
        </Text>
      </Modal>
    </>
  );
}
