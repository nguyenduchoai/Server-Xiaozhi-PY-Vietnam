/**
 * AgentDetailTabs - Tab-based layout for Agent Detail Page
 * Apple-style UX: Clean, organized, less cognitive load
 * 
 * Tabs:
 * 1. Tổng quan (Overview) - Agent info + Devices
 * 2. Cấu hình AI (AI Config) - Inline provider editor
 * 3. MCP Servers - MCP management  
 * 4. Bộ Nhớ (Memory)
 * 5. Nhắc nhở (Reminders)
 * 6. Lịch sử (History)
 * 7. Webhook API
 */

import { memo } from "react";
import { useTranslation } from "react-i18next";
import {
    Tabs,
    TabPane,
    Button,
    Tag,
    Select,
    Typography,
    Skeleton,
} from "@douyinfe/semi-ui";
import {
    IconInfoCircle,
    IconSetting,
    IconBell,
    IconPlus,
    IconUser,
    IconHistory,
    IconKey,
} from "@douyinfe/semi-icons";
import { Blocks, Bell as BellLucide, Puzzle, MessageCircle, Monitor } from "lucide-react";
import NotificationChannelsPanel from "@/components/NotificationChannelsPanel";

import {
    AgentDetailCard,
    DeviceListSection,
    ListReminders,
    AgentHistorySection,
    AgentMemorySection,
    WebhookApiSection,
    AgentAIConfigSection,
    FeatureModulesPanel,
    AgentBannerPanel,
} from "@/components";
import AgentChatPanel from "@/components/AgentChatPanel";
import type { AgentTemplateDetail, ReminderRead, ReminderStatus } from "@types";

const { Text } = Typography;

interface AgentDetailTabsProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    agent: any;
    agentId: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    devices: any[];
    templates: AgentTemplateDetail[];
    isLoading: boolean;
    onRefresh: () => void;
    onAddDevice: () => void;
    onAddTemplate: () => void;
    onDeleteTemplate: (templateId: string) => void;
    onSetDefaultTemplate: (templateId: string) => void;
    // MCP
    agentMcpData?: {
        data?: {
            mcp_selection_mode?: string;
            mode?: string;
            servers?: Array<{ reference: string; mcp_name: string }>;
        };
    };
    isUpdatingMcp: boolean;
    onManageMcp: () => void;
    // Reminders
    reminders?: { data: ReminderRead[] };
    isLoadingReminders: boolean;
    reminderStatus?: ReminderStatus;
    onReminderStatusChange: (status: ReminderStatus | undefined) => void;
    onAddReminder: () => void;
    onEditReminder: (reminder: ReminderRead) => void;
    onDeleteReminder: (reminderId: string) => void;
}

const AgentDetailTabsComponent = ({
    agent,
    agentId,
    devices,
    templates,
    isLoading,
    onRefresh,
    onAddDevice,
    agentMcpData,
    isUpdatingMcp,
    onManageMcp,
    reminders,
    isLoadingReminders,
    reminderStatus,
    onReminderStatusChange,
    onAddReminder,
    onEditReminder,
    onDeleteReminder,
}: AgentDetailTabsProps) => {
    const { t } = useTranslation("agents");

    // Count items for tab badges
    const reminderCount = reminders?.data?.length || 0;

    const currentMcpMode = agentMcpData?.data?.mcp_selection_mode || agentMcpData?.data?.mode;
    const mcpServerCount = agentMcpData?.data?.servers?.length || 0;

    // Count configured AI providers
    const aiProviderCount = [agent?.LLM, agent?.TTS, agent?.ASR, agent?.VLLM, agent?.Memory, agent?.Intent]
        .filter(Boolean).length;

    return (
        <Tabs type="line" defaultActiveKey="overview" size="large" tabBarStyle={{ marginBottom: '16px' }}>

            {/* Tab 1: Overview - Agent Info + Devices */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <IconInfoCircle />
                        {t("tab_overview", "Tổng quan")}
                    </span>
                }
                itemKey="overview"
            >
                <div className="space-y-4">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <AgentDetailCard agent={agent} onAddDevice={onAddDevice} />
                        <DeviceListSection
                            agentId={agentId}
                            devices={devices || []}
                            isLoading={isLoading}
                            onRefresh={onRefresh}
                        />
                    </div>
                </div>
            </TabPane>

            {/* Tab: Chat Test */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <MessageCircle size={16} />
                        Chat Test
                    </span>
                }
                itemKey="chat-test"
            >
                <AgentChatPanel agentId={agentId} agentName={agent?.agent_name} />
            </TabPane>

            {/* Tab 2: AI Configuration - Inline provider editor only */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <IconSetting />
                        {t("tab_ai_config", "Cấu hình AI")}
                        {aiProviderCount > 0 && (
                            <Tag size="small" color="blue">{aiProviderCount}</Tag>
                        )}
                    </span>
                }
                itemKey="ai-config"
            >
                <AgentAIConfigSection
                    agent={agent}
                    agentId={agentId}
                    templates={templates as any}
                    onRefresh={onRefresh}
                />
            </TabPane>

            {/* Tab 3: MCP Servers */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <Blocks size={16} />
                        MCP
                        {mcpServerCount > 0 && currentMcpMode === "selected" && (
                            <Tag size="small" color="violet">{mcpServerCount}</Tag>
                        )}
                        {currentMcpMode === "all" && (
                            <Tag size="small" color="blue">{t("all", "All")}</Tag>
                        )}
                    </span>
                }
                itemKey="mcp"
            >
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/10 to-purple-500/20">
                                <Blocks size={20} className="text-violet-500" />
                            </div>
                            <div>
                                <h3 className="font-semibold text-base">
                                    {t("manage_mcp_servers", "Quản lý MCP Servers")}
                                </h3>
                                <Text type="tertiary" size="small">
                                    {currentMcpMode === "all"
                                        ? t("all_servers_enabled", "Tất cả MCP servers có sẵn sẽ được sử dụng")
                                        : currentMcpMode === "selected"
                                            ? `${mcpServerCount} servers được chọn`
                                            : "Chưa cấu hình"}
                                </Text>
                            </div>
                        </div>
                        <Button
                            theme="solid"
                            type="primary"
                            onClick={onManageMcp}
                            disabled={isUpdatingMcp}
                            style={{
                                background: "linear-gradient(135deg, #8b5cf6, #6d28d9)",
                                border: "none",
                            }}
                        >
                            {t("common.manage", "Quản lý")}
                        </Button>
                    </div>

                    {/* Server list */}
                    {currentMcpMode === "selected" && mcpServerCount > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {agentMcpData?.data?.servers?.map((server) => (
                                <div
                                    key={server.reference}
                                    className="flex items-center gap-3 p-3.5 rounded-2xl transition-all hover:scale-[1.01]"
                                    style={{
                                        background: "linear-gradient(145deg, rgba(139,92,246,0.04), rgba(109,40,217,0.10))",
                                        border: "1px solid rgba(139,92,246,0.15)",
                                    }}
                                >
                                    <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-violet-500/10">
                                        <Blocks size={16} className="text-violet-500" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <Text strong className="block truncate text-sm">
                                            {server.mcp_name}
                                        </Text>
                                        <Text type="tertiary" size="small" className="block truncate font-mono text-xs">
                                            {server.reference}
                                        </Text>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {currentMcpMode === "all" && (
                        <div
                            className="p-6 rounded-2xl text-center"
                            style={{
                                background: "linear-gradient(145deg, rgba(59,130,246,0.04), rgba(99,102,241,0.08))",
                                border: "1px solid rgba(59,130,246,0.12)",
                            }}
                        >
                            <Blocks size={32} className="text-blue-400 mx-auto mb-2" />
                            <Text type="secondary" className="block">
                                Tất cả MCP servers có sẵn sẽ được sử dụng cho agent này
                            </Text>
                        </div>
                    )}

                    {!currentMcpMode && (
                        <div className="rounded-2xl border border-dashed border-gray-300 dark:border-gray-600 p-8 text-center">
                            <Blocks size={32} className="text-gray-300 mx-auto mb-3" />
                            <Text type="tertiary" className="block mb-3">
                                Chưa cấu hình MCP Servers
                            </Text>
                            <Button theme="light" onClick={onManageMcp}>
                                Cấu hình ngay
                            </Button>
                        </div>
                    )}
                </div>
            </TabPane>

            {/* Tab 4: Memory */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <IconUser />
                        {t("tab_memory", "Bộ Nhớ")}
                    </span>
                }
                itemKey="memory"
            >
                <AgentMemorySection agentId={agentId} />
            </TabPane>

            {/* Tab 5: Reminders */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <IconBell />
                        {t("tab_reminders", "Nhắc nhở")}
                        {reminderCount > 0 && (
                            <Tag size="small" color="orange">{reminderCount}</Tag>
                        )}
                    </span>
                }
                itemKey="reminders"
            >
                <div className="space-y-6">
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <h3 className="font-semibold text-base flex items-center gap-2">
                                <IconBell className="text-orange-500" />
                                {t("reminders", "Nhắc nhở (giờ địa phương)")}
                            </h3>
                            <div className="flex items-center gap-2">
                                <Select
                                    value={reminderStatus ?? "all"}
                                    onChange={(value) =>
                                        onReminderStatusChange(
                                            value === "all" ? undefined : (value as ReminderStatus)
                                        )
                                    }
                                    style={{ width: 130 }}
                                    optionList={[
                                        { value: "all", label: t("all", "Tất cả") },
                                        { value: "pending", label: t("pending", "Đang chờ") },
                                        { value: "delivered", label: t("delivered", "Đã gửi") },
                                        { value: "received", label: t("received", "Đã nhận") },
                                        { value: "failed", label: t("failed", "Thất bại") },
                                    ]}
                                />
                                <Button icon={<IconPlus />} theme="light" onClick={onAddReminder}>
                                    {t("add_reminder", "Thêm")}
                                </Button>
                            </div>
                        </div>
                        {isLoadingReminders ? (
                            <Skeleton.Image className="h-24 w-full" />
                        ) : (
                            <ListReminders
                                reminders={reminders?.data ?? []}
                                onEdit={onEditReminder}
                                onDelete={onDeleteReminder}
                            />
                        )}
                    </div>
                </div>
            </TabPane>

            {/* Tab: Tính Năng (Feature Modules) */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <Puzzle size={16} />
                        {t("tab_features", "Tính Năng")}
                    </span>
                }
                itemKey="features"
            >
                <FeatureModulesPanel agentId={agentId} agent={agent} onRefresh={onRefresh} />
            </TabPane>

            {/* Tab: Banners */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <Monitor size={16} />
                        Kiosk Banners
                    </span>
                }
                itemKey="banners"
            >
                <AgentBannerPanel agentId={agentId} agent={agent} onRefresh={onRefresh} />
            </TabPane>

            {/* Tab: History */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <IconHistory />
                        {t("tab_history", "Lịch sử")}
                    </span>
                }
                itemKey="history"
            >
                <AgentHistorySection agentId={agentId} />
            </TabPane>

            {/* Tab 7: Notification Channels */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <BellLucide size={16} />
                        {t("tab_notification_channels", "Kênh Thông Báo")}
                    </span>
                }
                itemKey="notification-channels"
            >
                <NotificationChannelsPanel
                    agentId={agentId}
                    agentName={agent?.agent_name}
                />
            </TabPane>

            {/* Tab 8: Webhook API */}
            <TabPane
                tab={
                    <span className="flex items-center gap-2">
                        <IconKey />
                        {t("tab_webhook", "Webhook API")}
                    </span>
                }
                itemKey="webhook"
            >
                <WebhookApiSection agentId={agentId} />
            </TabPane>
        </Tabs>
    );
};

export const AgentDetailTabs = memo(AgentDetailTabsComponent);
