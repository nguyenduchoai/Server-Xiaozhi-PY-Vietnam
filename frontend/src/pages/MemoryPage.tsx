import { toast } from "sonner";
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { PageHead } from "@/components";
import {
    Tabs,
    TabPane,
    Card,
    Tag,
    Button,
    Input,
    Select,
    Table,
    Modal,
    Typography,

    Form,
    TextArea,
    Empty
} from "@douyinfe/semi-ui";
import {
    IconPlus,
    IconSearch,
    IconRefresh,
    IconDelete,
    IconEdit
} from "@douyinfe/semi-icons";
import { Brain, Heart, RefreshCw } from "lucide-react"; // Custom icons

import memoryService from "@/services/memoryService";
import type { ConversationMemory, EmotionLog, EmotionSummary } from "@/services/memoryService";
import apiClient from "@/config/axios-instance";

const { Title, Text } = Typography;

interface Device {
    id: string;
    name: string;
    mac_address: string;
    is_online: boolean;
}

const getMemoryTypes = (t: any) => [
    { value: "fact", label: t("type_fact", "Fact") },
    { value: "preference", label: t("type_preference", "Preference") },
    { value: "habit", label: t("type_habit", "Habit") },
    { value: "context", label: t("type_context", "Context") },
    { value: "relationship", label: t("type_relationship", "Relationship") },
];

const getCategories = (t: any) => [
    { value: "personal", label: t("category_personal", "Personal") },
    { value: "professional", label: t("category_professional", "Professional") },
    { value: "social", label: t("category_social", "Social") },
    { value: "health", label: t("category_health", "Health") },
];

export const MemoryPage = () => {
    const { t } = useTranslation("memory");
    const [activeTab, setActiveTab] = useState("memory");
    const [devices, setDevices] = useState<Device[]>([]);
    const [selectedDevice, setSelectedDevice] = useState<string>("");
    const [memories, setMemories] = useState<ConversationMemory[]>([]);
    const [emotions, setEmotions] = useState<EmotionLog[]>([]);
    const [emotionSummary, setEmotionSummary] = useState<EmotionSummary | null>(null);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
    const [editingKey, setEditingKey] = useState<string | null>(null);
    const [newMemory, setNewMemory] = useState({
        key: "",
        value: "",
        memory_type: "fact",
        category: "personal",
    });

    // Confirm Modal State
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

    // Fetch devices on mount
    useEffect(() => {
        fetchDevices();
    }, []);

    // Fetch memories when device changes
    useEffect(() => {
        if (selectedDevice) {
            fetchMemories();
            fetchEmotions();
        }
    }, [selectedDevice]);

    const fetchDevices = async () => {
        try {
            const response = await apiClient.get("/user/devices/", {
                params: { page: 1, page_size: 100 }
            });
            const deviceList = response.data.data || [];
            setDevices(deviceList);
            if (deviceList.length > 0 && !selectedDevice) {
                setSelectedDevice(deviceList[0].id);
            }
        } catch (error) {
            console.error("Failed to fetch devices:", error);
            toast.error(t("error_fetch_devices", "Failed to fetch devices"));
        }
    };

    const fetchMemories = async () => {
        if (!selectedDevice) return;
        setLoading(true);
        try {
            const response = await memoryService.getDeviceMemories(selectedDevice);
            setMemories(response.data || []);
        } catch (error) {
            console.error("Failed to fetch memories:", error);
            setMemories([]);
        } finally {
            setLoading(false);
        }
    };

    const fetchEmotions = async () => {
        if (!selectedDevice) return;
        try {
            const [emotionsRes, summaryRes] = await Promise.all([
                memoryService.getRecentEmotions(selectedDevice, { hours: 24, limit: 50 }),
                memoryService.getEmotionSummary(selectedDevice, 24),
            ]);
            setEmotions(emotionsRes.data || []);
            setEmotionSummary(summaryRes.data);
        } catch (error) {
            console.error("Failed to fetch emotions:", error);
            setEmotions([]);
            setEmotionSummary(null);
        }
    };

    const handleSaveMemory = async () => {
        if (!selectedDevice || !newMemory.key || !newMemory.value) {
            toast.error(t("error_required_fields", "Please fill in all required fields"));
            return;
        }

        try {
            // If editing and key changed, delete old key first
            if (editingKey && editingKey !== newMemory.key) {
                await memoryService.deleteMemory(selectedDevice, editingKey);
            }

            await memoryService.createMemory(selectedDevice, newMemory);

            toast.success(editingKey ? t("memory_updated", "Memory updated") : t("memory_added", "Memory added"));
            setIsAddDialogOpen(false);
            setNewMemory({ key: "", value: "", memory_type: "fact", category: "personal" });
            setEditingKey(null);
            fetchMemories();
        } catch (error) {
            console.error("Failed to save memory:", error);
            toast.error(t("error_save_memory", "Failed to save memory"));
        }
    };

    const handleEditClick = (record: ConversationMemory) => {
        setNewMemory({
            key: record.key,
            value: record.value,
            memory_type: record.memory_type || "fact",
            category: record.category || "personal"
        });
        setEditingKey(record.key);
        setIsAddDialogOpen(true);
    };

    const handleDeleteMemory = async (key: string) => {
        if (!selectedDevice) return;
        try {
            await memoryService.deleteMemory(selectedDevice, key);
            toast.success("Memory deleted");
            fetchMemories();
        } catch (error) {
            console.error("Failed to delete memory:", error);
            toast.error("Failed to delete memory");
        }
    };

    const handleClearAll = async () => {
        if (!selectedDevice) return;
        showConfirm({
            title: t("clear_memories_title", "Clear All Memories"),
            content: t("clear_memories_confirm", "Are you sure you want to clear all memories for this device?"),
            okText: t("clear_all", "Clear All"),
            okType: "danger",
            onOk: async () => {
                try {
                    await memoryService.clearMemories(selectedDevice);
                    toast.success(t("memories_cleared", "All memories cleared"));
                    fetchMemories();
                } catch (error) {
                    console.error("Failed to clear memories:", error);
                    toast.error(t("error_clear_memories", "Failed to clear memories"));
                }
            }
        });
    };

    const filteredMemories = memories.filter(
        (m) =>
            m.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
            m.value.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const getEmotionEmoji = (emotion: string): string => {
        const emojiMap: Record<string, string> = {
            happy: "😊",
            sad: "😢",
            angry: "😠",
            surprised: "😲",
            neutral: "😐",
            excited: "🤩",
            worried: "😟",
            loving: "😍",
        };
        return emojiMap[emotion.toLowerCase()] || "😶";
    };

    // Columns for Memory Table
    const memoryColumns = [
        {
            title: t("memory_key", "Key"),
            dataIndex: 'key',
            key: 'key',
            render: (text: string) => <Text strong>{text}</Text>
        },
        {
            title: t("memory_value", "Value"),
            dataIndex: 'value',
            key: 'value',
            render: (text: string) => <Text ellipsis={{ showTooltip: true }} style={{ maxWidth: 300 }}>{text}</Text>
        },
        {
            title: t("memory_type", "Type"),
            dataIndex: 'memory_type',
            key: 'memory_type',
            render: (type: string) => <Tag>{type}</Tag>
        },
        {
            title: t("category", "Category"),
            dataIndex: 'category',
            key: 'category',
            render: (cat: string) => <Tag color="blue" type="ghost">{cat || "-"}</Tag>
        },
        {
            title: t("timestamp", "Updated"),
            dataIndex: 'updated_at',
            key: 'updated_at',
            render: (date: string) => <Text type="tertiary" size="small">{new Date(date).toLocaleDateString()}</Text>
        },
        {
            title: t("actions", "Action"),
            key: 'action',
            render: (_: any, record: ConversationMemory) => (
                <div className="flex items-center gap-2">
                    <Button
                        theme="borderless"
                        icon={<IconEdit />}
                        onClick={() => handleEditClick(record)}
                    />
                    <Button
                        type="danger"
                        theme="borderless"
                        icon={<IconDelete />}
                        onClick={() => handleDeleteMemory(record.key)}
                    />
                </div>
            )
        }
    ];

    // Columns for Emotions Table
    const emotionColumns = [
        {
            title: t("emotion", "Emotion"),
            dataIndex: 'emotion',
            key: 'emotion',
            render: (emotion: string) => (
                <div className="flex items-center gap-2">
                    <span className="text-xl">{getEmotionEmoji(emotion)}</span>
                    <span className="capitalize">{emotion}</span>
                </div>
            )
        },
        {
            title: t("intensity", "Intensity"),
            dataIndex: 'intensity',
            key: 'intensity',
            render: (intensity: number) => (
                <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                    <div
                        className="bg-blue-500 h-2.5 rounded-full"
                        style={{ width: `${intensity * 100}%` }}
                    />
                </div>
            )
        },
        {
            title: t("trigger", "Trigger"),
            dataIndex: 'trigger',
            key: 'trigger',
            render: (trigger: string) => <Text type="tertiary">{trigger || "-"}</Text>
        },
        {
            title: t("timestamp", "Time"),
            dataIndex: 'created_at',
            key: 'created_at',
            render: (date: string) => <Text type="tertiary" size="small">{new Date(date).toLocaleString()}</Text>
        }
    ];

    return (
        <>
            <PageHead
                title={t("page_title", "Memory Management")}
                description={t("page_description", "Manage memories, emotions, and proactive triggers for your AI")}
            />

            <div className="p-6 space-y-6">
                {/* Device Selector */}
                <div className="flex items-center gap-4 bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                    <Text strong style={{ minWidth: 'fit-content' }}>{t("select_device", "Select Device:")}</Text>
                    <Select
                        value={selectedDevice}
                        onChange={(v) => setSelectedDevice(v as string)}
                        style={{ width: 300 }}
                        placeholder={t("select_device_placeholder", "Select a device")}
                        optionList={devices.map(d => ({
                            value: d.id,
                            label: (
                                <div className="flex items-center gap-2">
                                    <span
                                        className={`w-2 h-2 rounded-full ${d.is_online ? "bg-green-500" : "bg-gray-400"}`}
                                    />
                                    {d.name || d.mac_address}
                                </div>
                            )
                        }))}
                        renderOptionItem={(item: any) => item.label}
                    />
                    <Button
                        icon={<IconRefresh />}
                        theme="borderless"
                        onClick={fetchDevices}
                    />
                </div>

                <Tabs type="card" activeKey={activeTab} onChange={setActiveTab} className="w-full">
                    <TabPane tab={
                        <span className="flex items-center gap-2">
                            <Brain className="h-4 w-4" />
                            {t("tab_memories", "Memories")}
                        </span>
                    } itemKey="memory">
                        <div className="pt-4">
                            <Card
                                title={
                                    <div>
                                        <Title heading={5}>{t("conversation_memories", "Conversation Memories")}</Title>
                                        <Text type="tertiary">{t("memory_desc", "View and manage what your AI agents remember about users.")}</Text>
                                    </div>
                                }
                                headerExtraContent={
                                    <div className="flex gap-2">
                                        <Button
                                            theme="solid"
                                            icon={<IconPlus />}
                                            disabled={!selectedDevice}
                                            onClick={() => setIsAddDialogOpen(true)}
                                        >
                                            {t("add_memory", "Add Memory")}
                                        </Button>
                                        <Button
                                            theme="light"
                                            type="danger"
                                            icon={<IconDelete />}
                                            disabled={!selectedDevice || memories.length === 0}
                                            onClick={handleClearAll}
                                        />
                                    </div>
                                }
                            >
                                {!selectedDevice ? (
                                    <Empty
                                        image={<Brain className="h-12 w-12 text-gray-300" />}
                                        description={t("select_agent_to_view", "Select a device to view memories")}
                                    />
                                ) : loading ? (
                                    <div className="flex items-center justify-center p-12">
                                        <RefreshCw className="h-6 w-6 animate-spin text-blue-500" />
                                    </div>
                                ) : memories.length === 0 ? (
                                    <Empty description={t("no_memories", "No memories stored yet. Start a conversation to build memory.")} />
                                ) : (
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2">
                                            <Input
                                                prefix={<IconSearch />}
                                                placeholder={t("search_memories", "Search memories...")}
                                                value={searchQuery}
                                                onChange={(val) => setSearchQuery(val)}
                                                style={{ maxWidth: 300 }}
                                            />
                                        </div>
                                        <Table
                                            columns={memoryColumns}
                                            dataSource={filteredMemories}
                                            pagination={{ pageSize: 10 }}
                                            rowKey="key"
                                        />
                                    </div>
                                )}
                            </Card>
                        </div>
                    </TabPane>

                    <TabPane tab={
                        <span className="flex items-center gap-2">
                            <Heart className="h-4 w-4" />
                            {t("tab_emotions", "Emotions")}
                        </span>
                    } itemKey="emotions">
                        <div className="pt-4 space-y-6">
                            {/* Emotion Summary */}
                            {emotionSummary && (
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <Card bodyStyle={{ padding: 16 }}>
                                        <div className="text-2xl font-bold">{emotionSummary.total_logs}</div>
                                        <Text type="tertiary" size="small">{t("total_logs_24h", "Total Logs (24h)")}</Text>
                                    </Card>
                                    <Card bodyStyle={{ padding: 16 }}>
                                        <div className="text-2xl font-bold flex items-center gap-2">
                                            {getEmotionEmoji(emotionSummary.dominant_emotion)}
                                            <span className="capitalize">{emotionSummary.dominant_emotion}</span>
                                        </div>
                                        <Text type="tertiary" size="small">{t("dominant_emotion", "Dominant Emotion")}</Text>
                                    </Card>
                                    <Card bodyStyle={{ padding: 16 }}>
                                        <div className="text-2xl font-bold">
                                            {(emotionSummary.average_intensity * 100).toFixed(0)}%
                                        </div>
                                        <Text type="tertiary" size="small">{t("avg_intensity", "Avg Intensity")}</Text>
                                    </Card>
                                    <Card bodyStyle={{ padding: 16 }}>
                                        <div className="text-2xl font-bold capitalize">{emotionSummary.mood_trend}</div>
                                        <Text type="tertiary" size="small">{t("mood_trend", "Mood Trend")}</Text>
                                    </Card>
                                </div>
                            )}

                            <Card
                                title={
                                    <div>
                                        <Title heading={5}>{t("emotional_intelligence", "Emotional Intelligence")}</Title>
                                        <Text type="tertiary">{t("emotion_desc", "Track emotional responses and sentiment analysis.")}</Text>
                                    </div>
                                }
                            >
                                {!selectedDevice ? (
                                    <Empty description="Select a device to view emotions" />
                                ) : emotions.length === 0 ? (
                                    <Empty description={t("no_emotion_data", "No emotion logs available")} />
                                ) : (
                                    <Table
                                        columns={emotionColumns}
                                        dataSource={emotions}
                                        pagination={{ pageSize: 10 }}
                                        rowKey="id"
                                    />
                                )}
                            </Card>
                        </div>
                    </TabPane>
                </Tabs>

                {/* Add/Edit Memory Modal */}
                <Modal
                    title={editingKey ? t("edit_memory", "Edit Memory") : t("add_memory_title", "Add New Memory")}
                    visible={isAddDialogOpen}
                    onOk={handleSaveMemory}
                    onCancel={() => {
                        setIsAddDialogOpen(false);
                        setEditingKey(null);
                        setNewMemory({ key: "", value: "", memory_type: "fact", category: "personal" });
                    }}
                    okText={t("save", "Save")}
                    cancelText={t("cancel", "Cancel")}
                >
                    <Form labelPosition="top">
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">{t("memory_key", "Key")}</label>
                            <Input
                                placeholder={t("memory_key_placeholder", "e.g., favorite_color")}
                                value={newMemory.key}
                                onChange={(val) => setNewMemory({ ...newMemory, key: val })}
                            />
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1">{t("memory_value", "Value")}</label>
                            <TextArea
                                placeholder={t("memory_value_placeholder", "e.g., blue")}
                                value={newMemory.value}
                                onChange={(val) => setNewMemory({ ...newMemory, value: val })}
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <label className="block text-sm font-medium text-gray-700 mb-1">{t("memory_type", "Type")}</label>
                                <Select
                                    value={newMemory.memory_type}
                                    onChange={(v) => setNewMemory({ ...newMemory, memory_type: v as string })}
                                    style={{ width: '100%' }}
                                    optionList={getMemoryTypes(t)}
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="block text-sm font-medium text-gray-700 mb-1">{t("category", "Category")}</label>
                                <Select
                                    value={newMemory.category}
                                    onChange={(v) => setNewMemory({ ...newMemory, category: v as string })}
                                    style={{ width: '100%' }}
                                    optionList={getCategories(t)}
                                />
                            </div>
                        </div>
                    </Form>
                </Modal>

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
