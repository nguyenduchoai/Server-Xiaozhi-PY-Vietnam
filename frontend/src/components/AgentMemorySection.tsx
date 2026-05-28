/**
 * AgentMemorySection - Embed memory list in Agent Detail tabs
 * Simplified version of AgentMemoryPage for tab display
 */

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button, Tag, Skeleton, Modal, Input, Typography, Empty, Select, Card, Pagination, Toast } from "@douyinfe/semi-ui";
import type { TagColor } from "@douyinfe/semi-ui/lib/es/tag";
import { IconDelete, IconPlus, IconEdit, IconSearch } from "@douyinfe/semi-icons";
import apiClient from "@/config/axios-instance";

const { Text } = Typography;

interface MemoryEntry {
    id: string;
    content: string;
    primary_sector: string;
    sectors: string[];
    tags: string[];
    salience: number;
    created_at: string;
    last_seen_at: string;
}

interface MemoryListResponse {
    items: MemoryEntry[];
    total: number;
    limit: number;
    offset: number;
}

const SECTORS = [
    { value: "semantic", label: "Personal", color: "blue" },
    { value: "episodic", label: "Episodic", color: "green" },
    { value: "procedural", label: "Procedural", color: "orange" },
    { value: "emotional", label: "Emotional", color: "pink" },
    { value: "reflective", label: "Reflective", color: "purple" },
];

interface AgentMemorySectionProps {
    agentId: string;
}

export function AgentMemorySection({ agentId }: AgentMemorySectionProps) {
    const { t } = useTranslation("agents");
    const [memories, setMemories] = useState<MemoryEntry[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [sectorFilter, setSectorFilter] = useState<string | undefined>(undefined);
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 10;

    // Dialog states
    const [addModalOpen, setAddModalOpen] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [memoryToDelete, setMemoryToDelete] = useState<string | null>(null);
    const [editEntry, setEditEntry] = useState<MemoryEntry | null>(null);
    const [formData, setFormData] = useState({ content: "", sector: "semantic", tags: "" });
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Fetch memories
    const fetchMemories = async () => {
        setIsLoading(true);
        try {
            const params: any = {
                limit: pageSize,
                offset: (currentPage - 1) * pageSize,
            };
            if (searchQuery) params.query = searchQuery;
            if (sectorFilter && sectorFilter !== "all") params.sector = sectorFilter;

            const response = await apiClient.get<{ data: MemoryListResponse }>(
                `/agents/${agentId}/knowledge-base/items`,
                { params }
            );
            setMemories(response.data.data?.items || []);
            setTotal(response.data.data?.total || 0);
        } catch (error) {
            console.error("Failed to fetch memories:", error);
            setMemories([]);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchMemories();
    }, [agentId, currentPage, sectorFilter]);

    const handleSearch = () => {
        setCurrentPage(1);
        fetchMemories();
    };

    const handleAddMemory = () => {
        setEditEntry(null);
        setFormData({ content: "", sector: "semantic", tags: "" });
        setAddModalOpen(true);
    };

    const handleEditMemory = (entry: MemoryEntry) => {
        setEditEntry(entry);
        setFormData({
            content: entry.content,
            sector: entry.primary_sector || "semantic",
            tags: entry.tags?.join(", ") || "",
        });
        setAddModalOpen(true);
    };

    const handleDeleteMemory = (entryId: string) => {
        setMemoryToDelete(entryId);
        setDeleteModalOpen(true);
    };

    const handleConfirmDelete = async () => {
        if (!memoryToDelete) return;
        try {
            await apiClient.delete(`/agents/${agentId}/knowledge-base/items/${memoryToDelete}`);
            Toast.success(t("memory_deleted", "Đã xóa"));
            fetchMemories();
        } catch (error) {
            Toast.error(t("delete_failed", "Xóa thất bại"));
        }
        setDeleteModalOpen(false);
        setMemoryToDelete(null);
    };

    const handleSubmit = async () => {
        if (!formData.content.trim()) return;
        setIsSubmitting(true);
        try {
            const payload = {
                content: formData.content,
                sector: formData.sector,
                tags: formData.tags.split(",").map((t) => t.trim()).filter(Boolean),
            };

            if (editEntry) {
                await apiClient.patch(`/agents/${agentId}/knowledge-base/items/${editEntry.id}`, {
                    content: formData.content,
                    tags: payload.tags,
                });
                Toast.success(t("memory_updated", "Đã cập nhật"));
            } else {
                await apiClient.post(`/agents/${agentId}/knowledge-base/items`, {
                    content: formData.content,
                    sector: formData.sector,
                    tags: [...payload.tags, "__source:memory"],
                });
                Toast.success(t("memory_added", "Đã thêm"));
            }
            fetchMemories();
            setAddModalOpen(false);
        } catch (error) {
            Toast.error(t("save_failed", "Lưu thất bại"));
        } finally {
            setIsSubmitting(false);
        }
    };

    const getSectorColor = (sector: string): TagColor => {
        const colorMap: Record<string, TagColor> = {
            semantic: "blue",
            episodic: "green",
            procedural: "orange",
            emotional: "pink",
            reflective: "purple",
        };
        return colorMap[sector] || "grey";
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString("vi-VN");
    };

    if (isLoading && memories.length === 0) {
        return (
            <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                    <Skeleton.Paragraph key={i} rows={2} />
                ))}
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                    <Input
                        prefix={<IconSearch />}
                        placeholder={t("search_memory", "Tìm kiếm...")}
                        value={searchQuery}
                        onChange={(v) => setSearchQuery(v)}
                        onEnterPress={handleSearch}
                        style={{ width: 200 }}
                    />
                    <Select
                        placeholder={t("filter_sector", "Loại")}
                        value={sectorFilter}
                        onChange={(v) => setSectorFilter(v as string)}
                        style={{ width: 120 }}
                        optionList={[
                            { value: "all", label: t("all", "Tất cả") },
                            ...SECTORS.map((s) => ({ value: s.value, label: s.label })),
                        ]}
                    />
                </div>
                <Button icon={<IconPlus />} theme="solid" onClick={handleAddMemory}>
                    {t("add_memory", "Thêm")}
                </Button>
            </div>

            {/* Memory Count */}
            <Text type="tertiary" size="small">
                {total} {t("memories", "bộ nhớ")}
            </Text>

            {/* Memory List */}
            {memories.length === 0 ? (
                <Empty
                    title={t("no_memories", "Chưa có bộ nhớ")}
                    description={t("no_memories_desc", "Agent chưa ghi nhớ thông tin nào")}
                />
            ) : (
                <div className="space-y-2">
                    {memories.map((entry) => (
                        <Card key={entry.id} bodyStyle={{ padding: 12 }}>
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                        <Tag size="small" color={getSectorColor(entry.primary_sector)}>
                                            {entry.primary_sector}
                                        </Tag>
                                        {entry.tags?.map((tag) => (
                                            <Tag key={tag} size="small" type="ghost">
                                                {tag}
                                            </Tag>
                                        ))}
                                    </div>
                                    <Text className="block">{entry.content}</Text>
                                    <Text type="tertiary" size="small" className="mt-1 block">
                                        {formatDate(entry.created_at)}
                                    </Text>
                                </div>
                                <div className="flex items-center gap-1">
                                    <Button
                                        icon={<IconEdit />}
                                        theme="borderless"
                                        size="small"
                                        onClick={() => handleEditMemory(entry)}
                                    />
                                    <Button
                                        icon={<IconDelete />}
                                        theme="borderless"
                                        type="danger"
                                        size="small"
                                        onClick={() => handleDeleteMemory(entry.id)}
                                    />
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            )}

            {/* Pagination */}
            {total > pageSize && (
                <div className="flex justify-center">
                    <Pagination
                        currentPage={currentPage}
                        total={total}
                        pageSize={pageSize}
                        onChange={(page) => setCurrentPage(page)}
                    />
                </div>
            )}

            {/* Add/Edit Modal */}
            <Modal
                title={editEntry ? t("edit_memory", "Sửa bộ nhớ") : t("add_memory", "Thêm bộ nhớ")}
                visible={addModalOpen}
                onCancel={() => setAddModalOpen(false)}
                footer={
                    <div className="flex justify-end gap-2">
                        <Button onClick={() => setAddModalOpen(false)}>
                            {t("common:cancel", "Hủy")}
                        </Button>
                        <Button
                            theme="solid"
                            onClick={handleSubmit}
                            loading={isSubmitting}
                            disabled={!formData.content.trim()}
                        >
                            {t("save", "Lưu")}
                        </Button>
                    </div>
                }
            >
                <div className="space-y-4">
                    <div>
                        <Text strong size="small" className="block mb-1">
                            {t("memory_content", "Nội dung")}
                        </Text>
                        <Input
                            value={formData.content}
                            onChange={(v) => setFormData({ ...formData, content: v })}
                            placeholder={t("memory_placeholder", "VD: Tôi thích ăn phở")}
                        />
                    </div>
                    <div>
                        <Text strong size="small" className="block mb-1">
                            {t("memory_sector", "Loại")}
                        </Text>
                        <Select
                            value={formData.sector}
                            onChange={(v) => setFormData({ ...formData, sector: v as string })}
                            style={{ width: "100%" }}
                            optionList={SECTORS.map((s) => ({ value: s.value, label: s.label }))}
                        />
                    </div>
                    <div>
                        <Text strong size="small" className="block mb-1">
                            {t("memory_tags", "Tags (phân cách bằng dấu phẩy)")}
                        </Text>
                        <Input
                            value={formData.tags}
                            onChange={(v) => setFormData({ ...formData, tags: v })}
                            placeholder="food, preference"
                        />
                    </div>
                </div>
            </Modal>

            {/* Delete Confirmation */}
            <Modal
                title={t("delete_memory_confirm", "Xóa bộ nhớ?")}
                visible={deleteModalOpen}
                onCancel={() => setDeleteModalOpen(false)}
                footer={
                    <div className="flex justify-end gap-2">
                        <Button onClick={() => setDeleteModalOpen(false)}>
                            {t("common:cancel", "Hủy")}
                        </Button>
                        <Button type="danger" theme="solid" onClick={handleConfirmDelete}>
                            {t("delete", "Xóa")}
                        </Button>
                    </div>
                }
            >
                <Text>{t("delete_memory_warning", "Bộ nhớ này sẽ bị xóa vĩnh viễn.")}</Text>
            </Modal>
        </div>
    );
}
