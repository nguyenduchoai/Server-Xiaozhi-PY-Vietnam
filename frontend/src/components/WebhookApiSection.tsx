/**
 * WebhookApiSection - Inline webhook management for Agent Detail tabs
 * Full-featured webhook API key management
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
    useGetWebhookConfig,
    useCreateWebhookConfig,
    useDeleteWebhookConfig,
} from "@/queries/agent-queries";
import { Button, Input, Tag, Typography, Card, Banner, Spin, Modal, Toast } from "@douyinfe/semi-ui";
import { IconCopy, IconEyeOpened, IconEyeClosed, IconDelete, IconPlus } from "@douyinfe/semi-icons";

const { Text } = Typography;

interface WebhookApiSectionProps {
    agentId: string;
}

export function WebhookApiSection({ agentId }: WebhookApiSectionProps) {
    const { t } = useTranslation("agents");
    const [showKey, setShowKey] = useState(false);
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

    const { data: webhookConfig, isLoading: isLoadingConfig } = useGetWebhookConfig(agentId, true);
    const { mutateAsync: createWebhookConfig, isPending: isCreatingConfig } = useCreateWebhookConfig(agentId);
    const { mutateAsync: deleteWebhookConfig, isPending: isDeletingConfig } = useDeleteWebhookConfig(agentId);

    const apiKey = webhookConfig?.data?.api_key;

    const handleCreateKey = async () => {
        try {
            await createWebhookConfig();
            setShowKey(true);
            Toast.success(t("key_created", "Đã tạo API Key"));
        } catch (error) {
            Toast.error(t("create_failed", "Tạo thất bại"));
        }
    };

    const handleDeleteKey = async () => {
        try {
            await deleteWebhookConfig();
            setShowKey(false);
            setDeleteConfirmOpen(false);
            Toast.success(t("key_deleted", "Đã xóa API Key"));
        } catch (error) {
            Toast.error(t("delete_failed", "Xóa thất bại"));
        }
    };

    const handleCopyUrl = () => {
        const url = `POST ${window.location.origin}/api/v1/agents/${agentId}/webhook?token=${apiKey || "YOUR_API_KEY"}`;
        navigator.clipboard.writeText(url);
        Toast.success(t("copied", "Đã copy!"));
    };

    const handleCopyKey = () => {
        if (apiKey) {
            navigator.clipboard.writeText(apiKey);
            Toast.success(t("copied", "Đã copy!"));
        }
    };

    const maskKey = (key: string): string => {
        if (key.length <= 8) return key;
        return key.slice(0, 4) + "•".repeat(key.length - 8) + key.slice(-4);
    };

    if (isLoadingConfig) {
        return (
            <div className="flex items-center justify-center py-8">
                <Spin />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Step 1: Quản lý API Key */}
            <Card title={<Text strong>1️⃣ {t("manage_api_key", "Quản lý API Key")}</Text>}>
                {apiKey ? (
                    <div className="space-y-3">
                        <div className="flex items-center gap-2">
                            <Tag color="green">{t("key_active", "Key đã kích hoạt")}</Tag>
                        </div>

                        <div className="flex gap-2">
                            <Input
                                type={showKey ? "text" : "password"}
                                value={showKey ? apiKey : maskKey(apiKey)}
                                readOnly
                                className="font-mono flex-1"
                            />
                            <Button
                                icon={showKey ? <IconEyeClosed /> : <IconEyeOpened />}
                                onClick={() => setShowKey(!showKey)}
                            />
                            <Button icon={<IconCopy />} onClick={handleCopyKey} />
                            <Button
                                icon={<IconDelete />}
                                type="danger"
                                onClick={() => setDeleteConfirmOpen(true)}
                            />
                        </div>
                    </div>
                ) : (
                    <div className="space-y-3">
                        <Banner
                            type="warning"
                            description={t("no_webhook_key", "Chưa có API Key. Tạo một key để sử dụng webhook.")}
                        />
                        <Button
                            theme="solid"
                            icon={<IconPlus />}
                            onClick={handleCreateKey}
                            loading={isCreatingConfig}
                        >
                            {t("create_api_key", "Tạo API Key")}
                        </Button>
                    </div>
                )}
            </Card>

            {/* Step 2: Endpoint URL */}
            <Card title={<Text strong>2️⃣ {t("endpoint_url", "Endpoint URL")}</Text>}>
                <div className="space-y-3">
                    <code className="text-sm bg-gray-100 px-3 py-2 rounded border block overflow-x-auto">
                        POST {window.location.origin}/api/v1/agents/{agentId}/webhook?token={apiKey ? "***" : "YOUR_API_KEY"}
                    </code>
                    <Button icon={<IconCopy />} theme="light" onClick={handleCopyUrl}>
                        {t("copy_url", "Copy URL")}
                    </Button>
                </div>
            </Card>

            {/* Step 3: Request Body */}
            <Card title={<Text strong>3️⃣ {t("request_body", "Request Body (JSON)")}</Text>}>
                <pre className="text-sm bg-gray-100 px-3 py-2 rounded border overflow-x-auto">
                    {`{
  "message": "Xin chào Agent!"
}`}
                </pre>
            </Card>

            {/* Step 4: Hướng dẫn */}
            <Card title={<Text strong>4️⃣ {t("usage_guide", "Hướng dẫn sử dụng")}</Text>}>
                <ul className="list-disc list-inside space-y-2 text-sm text-gray-600">
                    <li>Truyền token qua query parameter <code>?token=YOUR_KEY</code> hoặc header <code>X-Agent-Token</code></li>
                    <li>Request Body phải chứa field <code>"message"</code> (bắt buộc)</li>
                    <li>Response trả về JSON với nội dung phản hồi từ AI</li>
                    <li>Giữ API Key an toàn, không chia sẻ công khai</li>
                    <li>Xoá và tạo key mới định kỳ để bảo mật</li>
                </ul>
            </Card>

            {/* Example cURL */}
            <Card title={<Text strong>📋 {t("example_curl", "Ví dụ cURL")}</Text>}>
                <pre className="text-sm bg-gray-900 text-green-400 px-3 py-2 rounded overflow-x-auto">
                    {`curl -X POST "${window.location.origin}/api/v1/agents/${agentId}/webhook?token=YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Xin chào!"}'`}
                </pre>
            </Card>

            {/* Warning */}
            <Banner
                type="warning"
                icon={null}
                description={
                    <Text>
                        ⚠️ {t("webhook_warning", "Giữ bí mật API Key. Không chia sẻ công khai. Key có thể bị revoke nếu phát hiện lạm dụng.")}
                    </Text>
                }
            />

            {/* Delete Confirmation */}
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
                            {t("delete", "Xóa")}
                        </Button>
                    </div>
                }
            >
                <Text>
                    {t("delete_api_key_warning", "Webhook sẽ không còn hoạt động sau khi xoá. Hành động này không thể hoàn tác.")}
                </Text>
            </Modal>
        </div>
    );
}
