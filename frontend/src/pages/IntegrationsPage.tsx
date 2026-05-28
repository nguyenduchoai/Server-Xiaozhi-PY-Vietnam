/**
 * IntegrationsPage — Centralized channel configuration.
 *
 * Users configure Telegram, Zalo OA, SMTP, IMAP once here.
 * Agents/Meetings/Education just reference connection IDs.
 *
 * Menu: Settings → Tích hợp
 */

import { useState, useEffect, useCallback } from "react";
import {
    Card, Typography, Button, Input, Switch, Toast, Tag, Space,
    Modal, Spin,
} from "@douyinfe/semi-ui";
import { IconPlus, IconRefresh } from "@douyinfe/semi-icons";
import {
    Send, Bot, Mail, Inbox, TestTube, Eye, EyeOff,
    CheckCircle2, XCircle, Plug,
    Trash2, Edit3, Plus,
} from "lucide-react";
import connectionsApi, {
    type UserConnection,
    type ConnectionType,
    type ConnectionCreate,
} from "@/services/connectionsApi";

const { Title, Text, Paragraph } = Typography;

// ============ Channel Metadata ============

const CHANNEL_META: Record<ConnectionType, {
    icon: React.ReactNode;
    label: string;
    color: string;
    description: string;
    configFields: { key: string; label: string; type: string; placeholder?: string; required?: boolean }[];
}> = {
    telegram: {
        icon: <Send className="h-5 w-5" />,
        label: "Telegram Bot",
        color: "#0088cc",
        description: "Gửi thông báo qua Telegram Bot API",
        configFields: [
            { key: "bot_token", label: "Bot Token", type: "password", placeholder: "123456:ABC...", required: true },
        ],
    },
    zalo_oa: {
        icon: <Bot className="h-5 w-5" />,
        label: "Zalo OA Bot",
        color: "#0050cc",
        description: "Gửi thông báo qua Zalo Official Account",
        configFields: [
            { key: "oa_access_token", label: "OA Access Token", type: "password", placeholder: "Zalo OA Access Token", required: true },
        ],
    },
    smtp: {
        icon: <Mail className="h-5 w-5" />,
        label: "SMTP (Gửi Email)",
        color: "#e74c3c",
        description: "Gửi email thông báo qua SMTP server",
        configFields: [
            { key: "host", label: "SMTP Host", type: "text", placeholder: "smtp.gmail.com", required: true },
            { key: "port", label: "Port", type: "number", placeholder: "587" },
            { key: "secure", label: "SSL/TLS", type: "boolean" },
            { key: "username", label: "Username/Email", type: "text", placeholder: "user@gmail.com", required: true },
            { key: "password", label: "Password/App Password", type: "password", placeholder: "App password", required: true },
            { key: "from_name", label: "From Name", type: "text", placeholder: "AI Assistant" },
            { key: "from_email", label: "From Email", type: "text", placeholder: "user@gmail.com" },
        ],
    },
    imap: {
        icon: <Inbox className="h-5 w-5" />,
        label: "IMAP (Nhận Email)",
        color: "#27ae60",
        description: "Nhận và xử lý email qua IMAP server",
        configFields: [
            { key: "host", label: "IMAP Host", type: "text", placeholder: "imap.gmail.com", required: true },
            { key: "port", label: "Port", type: "number", placeholder: "993" },
            { key: "secure", label: "SSL/TLS", type: "boolean" },
            { key: "username", label: "Username/Email", type: "text", placeholder: "user@gmail.com", required: true },
            { key: "password", label: "Password/App Password", type: "password", placeholder: "App password", required: true },
            { key: "folder", label: "Folder", type: "text", placeholder: "INBOX" },
            { key: "poll_interval", label: "Poll Interval (giây)", type: "number", placeholder: "60" },
        ],
    },
};

// ============ Secret Input ============

function SecretInput({ value, onChange, placeholder }: {
    value: string; onChange: (v: string) => void; placeholder?: string;
}) {
    const [visible, setVisible] = useState(false);
    return (
        <Input
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            type={visible ? "text" : "password"}
            suffix={
                <span onClick={() => setVisible(!visible)} style={{ cursor: "pointer" }}>
                    {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </span>
            }
        />
    );
}

// ============ Connection Card ============

function ConnectionCard({ conn, onEdit, onDelete, onTest, isTesting }: {
    conn: UserConnection;
    onEdit: () => void;
    onDelete: () => void;
    onTest: () => void;
    isTesting?: boolean;
}) {
    const meta = CHANNEL_META[conn.type] || CHANNEL_META.telegram;
    const isConnected = conn.status === "connected";
    const isError = conn.status === "error";
    const lastTest = conn.status_info?.last_test as { success?: boolean; error?: string } | undefined;

    return (
        <Card
            style={{
                borderLeft: `4px solid ${meta.color}`,
                borderRadius: 12,
                opacity: conn.enabled ? 1 : 0.6,
            }}
            bodyStyle={{ padding: "16px 20px" }}
        >
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                    <div
                        className="flex items-center justify-center w-10 h-10 rounded-lg"
                        style={{ backgroundColor: `${meta.color}15`, color: meta.color }}
                    >
                        {meta.icon}
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <Text strong>{conn.name}</Text>
                            <Tag color={conn.enabled ? "blue" : "grey"} size="small">
                                {conn.enabled ? "Bật" : "Tắt"}
                            </Tag>
                            {isConnected && (
                                <Tag color="green" size="small">
                                    <CheckCircle2 className="h-3 w-3 inline mr-1" />
                                    Kết nối
                                </Tag>
                            )}
                            {isError && (
                                <Tag color="red" size="small">
                                    <XCircle className="h-3 w-3 inline mr-1" />
                                    Lỗi
                                </Tag>
                            )}
                        </div>
                        <Text type="tertiary" size="small">{meta.label} • {meta.description}</Text>
                    </div>
                </div>

                <Space>
                    <Button
                        icon={<TestTube className="h-4 w-4" />}
                        size="small"
                        type="tertiary"
                        onClick={onTest}
                        loading={isTesting}
                    >
                        Test
                    </Button>
                    <Button
                        icon={<Edit3 className="h-4 w-4" />}
                        size="small"
                        type="tertiary"
                        onClick={onEdit}
                    />
                    <Button
                        icon={<Trash2 className="h-4 w-4" />}
                        size="small"
                        type="danger"
                        onClick={onDelete}
                    />
                </Space>
            </div>

            {/* Last test result */}
            {lastTest && (
                <div className="mt-2 pt-2 border-t" style={{ borderColor: "rgba(0,0,0,0.06)" }}>
                    <Text type="tertiary" size="small">
                        {"Test gần nhất: " + (lastTest.success ? "✅ Thành công" : "❌ " + (lastTest.error || "Lỗi"))}
                    </Text>
                </div>
            )}
        </Card>
    );
}

// ============ Add/Edit Connection Modal ============

function ConnectionFormModal({ visible, onClose, onSave, editing }: {
    visible: boolean;
    onClose: () => void;
    onSave: (data: ConnectionCreate | { config: Record<string, unknown>; name?: string; enabled?: boolean }) => void;
    editing?: UserConnection | null;
}) {
    const [type, setType] = useState<ConnectionType>(editing?.type as ConnectionType || "telegram");
    const [name, setName] = useState(editing?.name || "");
    const [enabled, setEnabled] = useState(editing?.enabled ?? true);
    const [config, setConfig] = useState<Record<string, unknown>>(editing?.config || {});
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (editing) {
            setType(editing.type as ConnectionType);
            setName(editing.name);
            setEnabled(editing.enabled);
            setConfig(editing.config || {});
        } else {
            setType("telegram");
            setName("");
            setEnabled(true);
            setConfig({});
        }
    }, [editing, visible]);

    const meta = CHANNEL_META[type];

    const handleSave = async () => {
        if (!name.trim()) {
            Toast.warning("Vui lòng nhập tên kết nối");
            return;
        }
        setSaving(true);
        try {
            if (editing) {
                await onSave({ name, config, enabled });
            } else {
                await onSave({ type, name, config, enabled });
            }
            onClose();
        } catch (err) {
            console.error(err);
        } finally {
            setSaving(false);
        }
    };

    const updateConfig = (key: string, value: unknown) => {
        setConfig(prev => ({ ...prev, [key]: value }));
    };

    return (
        <Modal
            title={
                <div className="flex items-center gap-2">
                    {editing ? <Edit3 className="h-5 w-5" /> : <Plus className="h-5 w-5" />}
                    <span>{editing ? "Sửa kết nối" : "Thêm kết nối mới"}</span>
                </div>
            }
            visible={visible}
            onCancel={onClose}
            footer={
                <div className="flex justify-end gap-2">
                    <Button onClick={onClose}>Hủy</Button>
                    <Button theme="solid" type="primary" onClick={handleSave} loading={saving}>
                        {editing ? "Cập nhật" : "Tạo kết nối"}
                    </Button>
                </div>
            }
            width={520}
        >
            <div className="space-y-4">
                {/* Type selector (only for new) */}
                {!editing && (
                    <div>
                        <Text strong size="small" className="block mb-2">Loại kết nối</Text>
                        <div className="grid grid-cols-5 gap-2">
                            {(Object.keys(CHANNEL_META) as ConnectionType[]).map(t => {
                                const m = CHANNEL_META[t];
                                const isActive = type === t;
                                return (
                                    <div
                                        key={t}
                                        onClick={() => { setType(t); setConfig({}); }}
                                        className="flex flex-col items-center gap-1 p-3 rounded-lg border cursor-pointer transition-all"
                                        style={{
                                            borderColor: isActive ? m.color : "#e0e0e0",
                                            backgroundColor: isActive ? `${m.color}10` : undefined,
                                        }}
                                    >
                                        <span style={{ color: isActive ? m.color : "#999" }}>{m.icon}</span>
                                        <Text size="small" style={{ color: isActive ? m.color : "#666" }}>
                                            {m.label.split(" ")[0]}
                                        </Text>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Name */}
                <div>
                    <Text strong size="small" className="block mb-1">Tên kết nối</Text>
                    <Input
                        value={name}
                        onChange={setName}
                        placeholder={`VD: ${meta.label} chính`}
                        prefix={<Plug className="h-4 w-4 text-gray-400" />}
                    />
                </div>

                {/* Enable */}
                <div className="flex items-center justify-between">
                    <Text>Kích hoạt</Text>
                    <Switch checked={enabled} onChange={setEnabled} />
                </div>

                {/* Config fields */}
                <div className="space-y-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                    <Text strong size="small" className="block">Cấu hình {meta.label}</Text>
                    {meta.configFields.map(field => (
                        <div key={field.key}>
                            <Text size="small" className="block mb-1">
                                {field.label}
                                {field.required && <span className="text-red-500 ml-1">*</span>}
                            </Text>
                            {field.type === "password" ? (
                                <SecretInput
                                    value={String(config[field.key] || "")}
                                    onChange={v => updateConfig(field.key, v)}
                                    placeholder={field.placeholder}
                                />
                            ) : field.type === "boolean" ? (
                                <Switch
                                    checked={Boolean(config[field.key] ?? true)}
                                    onChange={v => updateConfig(field.key, v)}
                                />
                            ) : field.type === "number" ? (
                                <Input
                                    type="number"
                                    value={String(config[field.key] || "")}
                                    onChange={v => updateConfig(field.key, v ? Number(v) : "")}
                                    placeholder={field.placeholder}
                                />
                            ) : (
                                <Input
                                    value={String(config[field.key] || "")}
                                    onChange={v => updateConfig(field.key, v)}
                                    placeholder={field.placeholder}
                                />
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </Modal>
    );
}

// ============ Main Page ============

export default function IntegrationsPage() {
    const [connections, setConnections] = useState<UserConnection[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAdd, setShowAdd] = useState(false);
    const [editing, setEditing] = useState<UserConnection | null>(null);
    const [testing, setTesting] = useState<string | null>(null);

    const fetchConnections = useCallback(async () => {
        try {
            const result = await connectionsApi.list();
            setConnections(result.connections);
        } catch (err) {
            console.error("Failed to load connections:", err);
            Toast.error("Không thể tải danh sách kết nối");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchConnections();
    }, [fetchConnections]);

    const handleCreate = async (data: ConnectionCreate) => {
        try {
            await connectionsApi.create(data as ConnectionCreate);
            Toast.success("Đã tạo kết nối mới");
            fetchConnections();
        } catch (err: unknown) {
            Toast.error(`Lỗi: ${(err as Error).message}`);
        }
    };

    const handleUpdate = async (data: { config?: Record<string, unknown>; name?: string; enabled?: boolean }) => {
        if (!editing) return;
        try {
            await connectionsApi.update(editing.id, data);
            Toast.success("Đã cập nhật kết nối");
            setEditing(null);
            fetchConnections();
        } catch (err: unknown) {
            Toast.error(`Lỗi: ${(err as Error).message}`);
        }
    };

    const handleDelete = (conn: UserConnection) => {
        Modal.confirm({
            title: "Xóa kết nối",
            content: `Bạn chắc chắn muốn xóa "${conn.name}"? Các agent đang sử dụng sẽ mất kết nối này.`,
            okText: "Xóa",
            cancelText: "Hủy",
            okButtonProps: { type: "danger" },
            onOk: async () => {
                try {
                    await connectionsApi.delete(conn.id);
                    Toast.success("Đã xóa kết nối");
                    fetchConnections();
                } catch (err: unknown) {
                    Toast.error(`Lỗi: ${(err as Error).message}`);
                }
            },
        });
    };

    const handleTest = async (conn: UserConnection) => {
        // Show modal with recipient input
        const placeholders: Record<string, string> = {
            telegram: "Chat ID (ví dụ: 123456789)",
            zalo_oa: "Follower ID",
            smtp: "Email (ví dụ: test@gmail.com)",
            imap: "",
        };

        let recipientValue = "";
        let messageValue = "🔔 Test từ Xiaozhi AI IOT";

        Modal.confirm({
            title: `Test gửi tin — ${conn.name}`,
            okText: "Gửi test",
            cancelText: "Hủy",
            content: (
                <div style={{ marginTop: 12 }}>
                    <Input
                        placeholder={placeholders[conn.type] || "Người nhận"}
                        onChange={(v) => { recipientValue = v; }}
                        style={{ marginBottom: 8 }}
                    />
                    <Input
                        placeholder="Nội dung tin nhắn"
                        defaultValue={messageValue}
                        onChange={(v) => { messageValue = v; }}
                    />
                    <Typography.Text type="tertiary" size="small" style={{ marginTop: 4, display: "block" }}>
                        {conn.type === "telegram" ? "Nhập Chat ID để gửi test" :
                         conn.type === "smtp" ? "Nhập email để gửi test" :
                         "Nhập ID người nhận"}
                    </Typography.Text>
                </div>
            ),
            onOk: async () => {
                if (!recipientValue.trim()) {
                    Toast.warning("Vui lòng nhập người nhận!");
                    return;
                }
                setTesting(conn.id);
                try {
                    const result = await connectionsApi.sendTest(conn.id, recipientValue.trim(), messageValue);
                    if (result.success) {
                        Toast.success(`✅ ${result.message || "Gửi thành công!"}`);
                    } else {
                        Toast.error(`❌ ${result.error || "Gửi thất bại"}`);
                    }
                    fetchConnections();
                } catch (err: unknown) {
                    Toast.error(`Lỗi: ${(err as Error).message}`);
                } finally {
                    setTesting(null);
                }
            },
        });
    };



    return (
        <div className="max-w-4xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <Title heading={3} className="!mb-1">
                        <Plug className="h-6 w-6 inline mr-2 text-blue-500" />
                        Tích hợp
                    </Title>
                    <Paragraph type="tertiary" className="!mb-0">
                        Cấu hình kênh kết nối một lần — sử dụng cho tất cả Agent, Meeting, Education
                    </Paragraph>
                </div>
                <Space>
                    <Button
                        icon={<IconRefresh />}
                        onClick={fetchConnections}
                        type="tertiary"
                    />
                    <Button
                        icon={<IconPlus />}
                        theme="solid"
                        type="primary"
                        onClick={() => setShowAdd(true)}
                    >
                        Thêm kết nối
                    </Button>
                </Space>
            </div>

            {/* Empty state */}
            {!loading && connections.length === 0 && (
                <Card style={{ borderRadius: 12 }}>
                    <div className="text-center py-12">
                        <Plug className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                        <Title heading={5} type="tertiary">Chưa có kết nối nào</Title>
                        <Paragraph type="tertiary">
                            Thêm kết nối Telegram, Zalo, Email để bắt đầu gửi thông báo
                        </Paragraph>
                        <Button
                            theme="solid"
                            type="primary"
                            icon={<IconPlus />}
                            onClick={() => setShowAdd(true)}
                            className="mt-4"
                        >
                            Thêm kết nối mới
                        </Button>
                    </div>
                </Card>
            )}

            {/* Loading */}
            {loading && (
                <div className="flex justify-center py-12">
                    <Spin size="large" tip="Đang tải..." />
                </div>
            )}

            {/* Connection list by type */}
            {!loading && connections.length > 0 && (
                <div className="space-y-4">
                    {connections.map(conn => (
                        <ConnectionCard
                            key={conn.id}
                            conn={conn}
                            onEdit={() => setEditing(conn)}
                            onDelete={() => handleDelete(conn)}
                            onTest={() => handleTest(conn)}
                            isTesting={testing === conn.id}
                        />
                    ))}
                </div>
            )}

            {/* Quick-add channel types */}
            {!loading && connections.length > 0 && (
                <Card
                    style={{ borderRadius: 12, borderStyle: "dashed" }}
                    bodyStyle={{ padding: 16 }}
                >
                    <div className="flex items-center justify-between">
                        <Text type="tertiary">Thêm kênh kết nối mới</Text>
                        <div className="flex gap-2">
                            {(Object.keys(CHANNEL_META) as ConnectionType[]).map(t => {
                                const m = CHANNEL_META[t];
                                return (
                                    <Button
                                        key={t}
                                        size="small"
                                        type="tertiary"
                                        icon={<span style={{ color: m.color }}>{m.icon}</span>}
                                        onClick={() => {
                                            setEditing(null);
                                            setShowAdd(true);
                                        }}
                                    >
                                        {m.label.split(" ")[0]}
                                    </Button>
                                );
                            })}
                        </div>
                    </div>
                </Card>
            )}

            {/* Add/Edit Modal */}
            <ConnectionFormModal
                visible={showAdd || !!editing}
                onClose={() => { setShowAdd(false); setEditing(null); }}
                onSave={(data) => editing ? handleUpdate(data) : handleCreate(data as ConnectionCreate)}
                editing={editing}
            />
        </div>
    );
}
