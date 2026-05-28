/**
 * NotificationChannelsPanel — Per-agent notification config.
 *
 * SAME UI as before (accordion sections) but WITHOUT credential config.
 * Credentials → Settings → Tích hợp (UserConnection).
 * This panel: enable/disable channels + pick recipients.
 *
 * Sections:
 *   1. Telegram Bot       → toggle + Chat IDs (TagInput)
 *   2. Zalo OA Bot        → toggle + Follower IDs (TagInput)
 *   3. Cấp độ cảnh báo    → escalation levels
 *   4. Báo cáo hàng ngày  → time + channels
 *
 * Each messaging channel maps to a UserConnection from Settings → Tích hợp.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import {
    Card, Typography, Button, Toast, Tag, Space, Switch, Spin,
    TagInput, Input, Collapsible, Select,
    Banner,
} from "@douyinfe/semi-ui";
import { IconChevronDown, IconChevronRight } from "@douyinfe/semi-icons";
import {
    Send, Bot, Bell, AlertTriangle,
    CalendarClock, Save, ExternalLink, Users, TestTube, RotateCcw,
    Plug,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import connectionsApi, { type UserConnection } from "@/services/connectionsApi";
import notificationChannelsApi, { type NotificationChannelsConfig } from "@/services/notificationChannelsApi";

const { Title, Text } = Typography;

// ============ Types ============

interface ChannelSectionProps {
    title: string;
    icon: React.ReactNode;
    tag?: { text: string; color: string };
    children: React.ReactNode;
    defaultOpen?: boolean;
}

// ============ Collapsible Section (same style as old panel) ============

function ChannelSection({ title, icon, tag, children, defaultOpen = false }: ChannelSectionProps) {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="border-b" style={{ borderColor: "rgba(0,0,0,0.06)" }}>
            <div
                className="flex items-center justify-between py-3 px-1 cursor-pointer hover:bg-gray-50 transition-colors rounded"
                onClick={() => setOpen(!open)}
            >
                <div className="flex items-center gap-3">
                    <span className="text-gray-500">{icon}</span>
                    <Text strong>{title}</Text>
                    {tag && (
                        <Tag size="small" color={tag.color as any} style={{ fontSize: 11 }}>
                            {tag.text}
                        </Tag>
                    )}
                </div>
                {open
                    ? <IconChevronDown style={{ color: "#999" }} />
                    : <IconChevronRight style={{ color: "#999" }} />
                }
            </div>
            <Collapsible isOpen={open}>
                <div className="pb-4 px-1">
                    {children}
                </div>
            </Collapsible>
        </div>
    );
}

// ============ Main Component ============

interface NotificationChannelsPanelProps {
    agentId: string;
    agentName?: string;
}

export default function NotificationChannelsPanel({ agentId }: NotificationChannelsPanelProps) {
    const navigate = useNavigate();
    const [connections, setConnections] = useState<UserConnection[]>([]);
    const [config, setConfig] = useState<NotificationChannelsConfig>({});
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [initialJson, setInitialJson] = useState("");

    // Connection maps by type
    const connByType = useMemo(() => {
        const map: Record<string, UserConnection> = {};
        connections.forEach(c => {
            if (!map[c.type]) map[c.type] = c; // Take first of each type
        });
        return map;
    }, [connections]);

    // Load
    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [{ connections: conns }, cfg] = await Promise.all([
                connectionsApi.list(),
                notificationChannelsApi.getConfig(agentId).catch(() => ({} as NotificationChannelsConfig)),
            ]);
            setConnections(conns);
            setConfig(cfg);
            setInitialJson(JSON.stringify(cfg));
        } catch (err) {
            console.error("Failed to load:", err);
        } finally {
            setLoading(false);
        }
    }, [agentId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const hasChanges = JSON.stringify(config) !== initialJson;

    // Update helpers
    const updateTelegram = (patch: Partial<NotificationChannelsConfig["telegram"]>) => {
        setConfig(prev => ({
            ...prev,
            telegram: { enabled: false, bot_token: "", chat_ids: [], ...prev.telegram, ...patch },
        }));
    };

    const updateZaloOA = (patch: Partial<NotificationChannelsConfig["zalo_oa"]>) => {
        setConfig(prev => ({
            ...prev,
            zalo_oa: { enabled: false, oa_access_token: "", user_ids: [], ...prev.zalo_oa, ...patch },
        }));
    };

    const updateEscalation = (patch: Partial<NotificationChannelsConfig["alert_escalation"]>) => {
        setConfig(prev => ({
            ...prev,
            alert_escalation: {
                enabled: false,
                levels: {
                    info: { channels: ["device"] },
                    warning: { channels: ["device", "telegram"] },
                    critical: { channels: ["device", "telegram", "zalo_oa"] },
                    sos: { channels: ["device", "telegram", "zalo_oa"] },
                },
                ...prev.alert_escalation,
                ...patch,
            },
        }));
    };

    const updateDailyReport = (patch: Partial<NotificationChannelsConfig["daily_report"]>) => {
        setConfig(prev => ({
            ...prev,
            daily_report: {
                enabled: false,
                time: "21:00",
                timezone: "Asia/Ho_Chi_Minh",
                channels: ["telegram"],
                ...prev.daily_report,
                ...patch,
            },
        }));
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const saved = await notificationChannelsApi.updateConfig(agentId, config);
            setConfig(saved);
            setInitialJson(JSON.stringify(saved));
            Toast.success("Đã lưu cấu hình kênh thông báo");
        } catch (err) {
            Toast.error(`Lỗi: ${(err as Error).message}`);
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        // Pre-check: if no channels are enabled for this agent
        if (activeCount === 0) {
            if (hasAnyConnection) {
                Toast.warning("Bạn đã có kết nối Telegram/Zalo nhưng chưa BẬT cho agent này. Hãy bật toggle ở từng kênh bên dưới rồi Lưu cấu hình trước.");
            } else {
                Toast.warning("Chưa có kênh nào. Vào Settings → Tích hợp để kết nối Telegram/Zalo trước.");
            }
            return;
        }
        setTesting(true);
        try {
            const result = await notificationChannelsApi.testNotification(agentId, {
                message: "🔔 Tin nhắn test từ Xiaozhi AI",
                level: "info",
            });
            const channels = Object.entries(result);
            const successes = channels.filter(([, r]) => r.success);
            if (successes.length > 0) {
                Toast.success(`✅ Gửi thành công: ${successes.map(([k]) => k).join(", ")}`);
            }
            const failures = channels.filter(([, r]) => !r.success);
            failures.forEach(([k, r]) => {
                Toast.error(`❌ ${k}: ${r.error || "Lỗi"}`);
            });
            if (channels.length === 0) {
                Toast.warning("API trả về 0 kênh. Hãy bật toggle Telegram/Zalo ở bên dưới → Lưu cấu hình → Test lại.");
            }
        } catch (err: any) {
            const msg = err?.response?.data?.detail || (err as Error).message;
            if (msg?.includes("No notification channels")) {
                Toast.warning("Chưa lưu cấu hình kênh cho agent này. Bật Telegram/Zalo → nhấn Lưu → Test lại.");
            } else {
                Toast.error(`Lỗi test: ${msg}`);
            }
        } finally {
            setTesting(false);
        }
    };

    const handleReset = () => {
        setConfig(JSON.parse(initialJson));
    };

    if (loading) {
        return (
            <div className="flex justify-center py-12">
                <Spin size="large" tip="Đang tải..." />
            </div>
        );
    }

    const telegramConn = connByType["telegram"];
    const zaloOAConn = connByType["zalo_oa"];
    const hasAnyConnection = connections.length > 0;

    // Status helper
    const connStatus = (conn?: UserConnection) => {
        if (!conn) return null;
        if (conn.status === "connected") return { text: "Đã kết nối", color: "green" };
        if (conn.status === "error") return { text: "Lỗi", color: "red" };
        return { text: "Chưa kết nối", color: "grey" };
    };

    // Count active channels
    const activeCount = [
        config.telegram?.enabled,
        config.zalo_oa?.enabled,
        config.alert_escalation?.enabled,
        config.daily_report?.enabled,
    ].filter(Boolean).length;

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <Title heading={5} className="!mb-0">
                    <Bell className="h-5 w-5 inline mr-2 text-blue-500" />
                    Kênh Thông Báo
                </Title>
                <Space>
                    <Button
                        icon={<TestTube className="h-4 w-4" />}
                        type="tertiary"
                        onClick={handleTest}
                        loading={testing}
                        size="small"
                    >
                        Test gửi
                    </Button>
                    <Button
                        icon={<Save className="h-4 w-4" />}
                        theme="solid"
                        type="primary"
                        onClick={handleSave}
                        loading={saving}
                        disabled={!hasChanges}
                    >
                        Lưu cấu hình
                    </Button>
                </Space>
            </div>

            {/* No connections banner */}
            {!hasAnyConnection && (
                <Banner
                    type="info"
                    description={
                        <div className="flex items-center justify-between">
                            <span>Chưa có kết nối nào. Vào Tích hợp để cấu hình Telegram, Zalo, Email...</span>
                            <Button
                                icon={<ExternalLink className="h-3.5 w-3.5" />}
                                size="small"
                                theme="solid"
                                onClick={() => navigate("/settings/integrations")}
                            >
                                Mở Tích hợp
                            </Button>
                        </div>
                    }
                />
            )}

            {/* === Channel Sections === */}
            <Card style={{ borderRadius: 12 }} bodyStyle={{ padding: "4px 16px" }}>

                {/* ── Telegram Bot ── */}
                <ChannelSection
                    title="Telegram Bot"
                    icon={<Send className="h-4 w-4 text-[#0088cc]" />}
                    tag={telegramConn ? connStatus(telegramConn) as any : undefined}
                    defaultOpen={!!config.telegram?.enabled}
                >
                    {!telegramConn ? (
                        <Banner type="warning" description={
                            <span>
                                Chưa cấu hình Telegram Bot.{" "}
                                <a onClick={() => navigate("/settings/integrations")} className="text-blue-500 cursor-pointer">
                                    Vào Tích hợp để thêm →
                                </a>
                            </span>
                        } />
                    ) : (
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <Text strong size="small">Kích hoạt Telegram</Text>
                                    <Text type="tertiary" size="small" className="block">
                                        Gửi thông báo qua {telegramConn.name}
                                    </Text>
                                </div>
                                <Switch
                                    checked={config.telegram?.enabled || false}
                                    onChange={(checked) => updateTelegram({ enabled: checked })}
                                />
                            </div>

                            {config.telegram?.enabled && (
                                <div>
                                    <Text size="small" type="tertiary" className="block mb-1">
                                        <Users className="h-3 w-3 inline mr-1" />
                                        Chat IDs nhận thông báo
                                    </Text>
                                    <TagInput
                                        value={config.telegram?.chat_ids || []}
                                        placeholder="Nhập Chat ID (số) rồi Enter"
                                        onChange={(vals) => updateTelegram({ chat_ids: (vals || []) as string[] })}
                                        separator=","
                                        showClear
                                    />
                                    <Text type="quaternary" size="small" className="block mt-1" style={{ fontSize: 11 }}>
                                        Chat ID cá nhân hoặc Group ID (số âm). Dùng @userinfobot để lấy ID.
                                    </Text>
                                </div>
                            )}
                        </div>
                    )}
                </ChannelSection>

                {/* ── Zalo OA Bot ── */}
                <ChannelSection
                    title="Zalo OA Bot"
                    icon={<Bot className="h-4 w-4 text-[#0050cc]" />}
                    tag={zaloOAConn
                        ? { text: "Official Account", color: "blue" }
                        : undefined
                    }
                >
                    {!zaloOAConn ? (
                        <Banner type="warning" description={
                            <span>
                                Chưa cấu hình Zalo OA.{" "}
                                <a onClick={() => navigate("/settings/integrations")} className="text-blue-500 cursor-pointer">
                                    Vào Tích hợp để thêm →
                                </a>
                            </span>
                        } />
                    ) : (
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <Text strong size="small">Kích hoạt Zalo OA</Text>
                                    <Text type="tertiary" size="small" className="block">
                                        Gửi qua {zaloOAConn.name}
                                    </Text>
                                </div>
                                <Switch
                                    checked={config.zalo_oa?.enabled || false}
                                    onChange={(checked) => updateZaloOA({ enabled: checked })}
                                />
                            </div>

                            {config.zalo_oa?.enabled && (
                                <div>
                                    <Text size="small" type="tertiary" className="block mb-1">
                                        <Users className="h-3 w-3 inline mr-1" />
                                        Follower IDs nhận tin
                                    </Text>
                                    <TagInput
                                        value={config.zalo_oa?.user_ids || []}
                                        placeholder="Nhập Follower ID rồi Enter"
                                        onChange={(vals) => updateZaloOA({ user_ids: (vals || []) as string[] })}
                                        separator=","
                                        showClear
                                    />
                                    <Text type="quaternary" size="small" className="block mt-1" style={{ fontSize: 11 }}>
                                        ID người theo dõi OA (lấy từ Zalo OA Admin → Quản lý người theo dõi)
                                    </Text>
                                </div>
                            )}
                        </div>
                    )}
                </ChannelSection>

                {/* ── Cấp độ cảnh báo (Escalation) ── */}
                <ChannelSection
                    title="Cấp độ cảnh báo (Escalation)"
                    icon={<AlertTriangle className="h-4 w-4 text-orange-500" />}
                    tag={config.alert_escalation?.enabled
                        ? { text: "Bật", color: "green" }
                        : undefined
                    }
                >
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <Text strong size="small">Kích hoạt Escalation</Text>
                                <Text type="tertiary" size="small" className="block">
                                    Tự động chuyển tiếp qua các kênh theo mức cảnh báo
                                </Text>
                            </div>
                            <Switch
                                checked={config.alert_escalation?.enabled || false}
                                onChange={(checked) => updateEscalation({ enabled: checked })}
                            />
                        </div>

                        {config.alert_escalation?.enabled && (
                            <div className="space-y-2 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                                {(["info", "warning", "critical", "sos"] as const).map(level => {
                                    const labels = {
                                        info: { label: "Thông tin", color: "blue", emoji: "ℹ️" },
                                        warning: { label: "Cảnh báo", color: "orange", emoji: "⚠️" },
                                        critical: { label: "Nghiêm trọng", color: "red", emoji: "🔴" },
                                        sos: { label: "SOS", color: "red", emoji: "🆘" },
                                    };
                                    const meta = labels[level];
                                    const channels = config.alert_escalation?.levels?.[level]?.channels || [];
                                    return (
                                        <div key={level} className="flex items-center justify-between">
                                            <Text size="small">
                                                {meta.emoji} {meta.label}
                                            </Text>
                                            <Select
                                                multiple
                                                value={channels}
                                                onChange={(vals) => {
                                                    const levels = { ...config.alert_escalation?.levels };
                                                    levels[level] = { channels: (vals || []) as string[] };
                                                    updateEscalation({ levels: levels as any });
                                                }}
                                                size="small"
                                                style={{ width: 260 }}
                                                placeholder="Chọn kênh..."
                                            >
                                                <Select.Option value="device">📱 Thiết bị</Select.Option>
                                                <Select.Option value="telegram">📨 Telegram</Select.Option>
                                                <Select.Option value="zalo_oa">💬 Zalo OA</Select.Option>
                                                <Select.Option value="email">📧 Email</Select.Option>
                                            </Select>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </ChannelSection>

                {/* ── Báo cáo hàng ngày ── */}
                <ChannelSection
                    title="Báo cáo hàng ngày"
                    icon={<CalendarClock className="h-4 w-4 text-green-500" />}
                    tag={config.daily_report?.enabled
                        ? { text: config.daily_report?.time || "21:00", color: "green" }
                        : undefined
                    }
                >
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <Text strong size="small">Kích hoạt Báo cáo</Text>
                                <Text type="tertiary" size="small" className="block">
                                    Tự động gửi báo cáo tóm tắt hằng ngày
                                </Text>
                            </div>
                            <Switch
                                checked={config.daily_report?.enabled || false}
                                onChange={(checked) => updateDailyReport({ enabled: checked })}
                            />
                        </div>

                        {config.daily_report?.enabled && (
                            <div className="space-y-3 bg-gray-50 dark:bg-gray-800 p-3 rounded-lg">
                                <div className="flex items-center gap-4">
                                    <div>
                                        <Text size="small" className="block mb-1">Giờ gửi</Text>
                                        <Input
                                            value={config.daily_report?.time || "21:00"}
                                            onChange={(val) => updateDailyReport({ time: val })}
                                            placeholder="21:00"
                                            style={{ width: 100 }}
                                            size="small"
                                        />
                                    </div>
                                    <div>
                                        <Text size="small" className="block mb-1">Múi giờ</Text>
                                        <Select
                                            value={config.daily_report?.timezone || "Asia/Ho_Chi_Minh"}
                                            onChange={(val) => updateDailyReport({ timezone: val as string })}
                                            size="small"
                                            style={{ width: 180 }}
                                        >
                                            <Select.Option value="Asia/Ho_Chi_Minh">Asia/Ho_Chi_Minh</Select.Option>
                                            <Select.Option value="Asia/Bangkok">Asia/Bangkok</Select.Option>
                                            <Select.Option value="UTC">UTC</Select.Option>
                                        </Select>
                                    </div>
                                </div>
                                <div>
                                    <Text size="small" className="block mb-1">Gửi qua kênh</Text>
                                    <Select
                                        multiple
                                        value={config.daily_report?.channels || ["telegram"]}
                                        onChange={(vals) => updateDailyReport({ channels: (vals || []) as string[] })}
                                        size="small"
                                        style={{ width: "100%" }}
                                    >
                                        <Select.Option value="telegram">📨 Telegram</Select.Option>
                                        <Select.Option value="zalo_oa">💬 Zalo OA</Select.Option>
                                        <Select.Option value="email">📧 Email</Select.Option>
                                        <Select.Option value="device">📱 Thiết bị</Select.Option>
                                    </Select>
                                </div>
                            </div>
                        )}
                    </div>
                </ChannelSection>
            </Card>

            {/* Footer */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Text type="tertiary" size="small">
                        {activeCount > 0
                            ? `${activeCount} kênh đang bật`
                            : "Chưa cấu hình kênh thông báo nào"
                        }
                    </Text>
                    {hasAnyConnection && (
                        <Button
                            icon={<Plug className="h-3 w-3" />}
                            type="tertiary"
                            size="small"
                            onClick={() => navigate("/settings/integrations")}
                            style={{ fontSize: 12 }}
                        >
                            Quản lý kết nối
                        </Button>
                    )}
                </div>
                <Space>
                    <Button
                        icon={<RotateCcw className="h-3.5 w-3.5" />}
                        onClick={handleReset}
                        disabled={!hasChanges}
                        size="small"
                    >
                        Reset
                    </Button>
                    <Button
                        icon={<Save className="h-4 w-4" />}
                        theme="solid"
                        type="primary"
                        onClick={handleSave}
                        loading={saving}
                        disabled={!hasChanges}
                    >
                        Lưu cấu hình
                    </Button>
                </Space>
            </div>
        </div>
    );
}
