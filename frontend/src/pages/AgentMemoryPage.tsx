/**
 * Agent Memory Page - Personal Facts Storage
 * 
 * Uses OpenMemory for semantic memory per agent.
 * This is for personal information like:
 * - "Tôi có 2 con chó"
 * - "Tôi thích màu xanh"
 * 
 * Different from Knowledge Base which stores documents (PDFs, etc.)
 */

import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AlertCircle, ArrowLeft, Brain, Plus, Search, Trash2, Edit2, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { useAgentDetail } from "@/queries/agent-queries";
import { PageHead } from "@/components/PageHead";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";

import apiClient from "@/config/axios-instance";

// Types
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

type MemorySector = "semantic" | "procedural" | "episodic" | "emotional" | "reflective";

const SECTORS: { value: MemorySector; label: string; description: string }[] = [
    { value: "semantic", label: "Personal", description: "Thông tin cá nhân về bạn" },
    { value: "episodic", label: "Episodic", description: "Sự kiện & trải nghiệm" },
    { value: "procedural", label: "Procedural", description: "Thói quen & quy trình" },
    { value: "emotional", label: "Emotional", description: "Cảm xúc & sở thích" },
    { value: "reflective", label: "Reflective", description: "Suy nghĩ & nhận định" },
];

export const AgentMemoryPage = () => {
    const { agentId } = useParams<{ agentId: string }>();
    const navigate = useNavigate();
    const { t } = useTranslation("agents");

    // State
    const [memories, setMemories] = useState<MemoryEntry[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedSector, setSelectedSector] = useState<MemorySector | "all">("all");

    // Dialog state
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editingEntry, setEditingEntry] = useState<MemoryEntry | null>(null);
    const [formData, setFormData] = useState({
        content: "",
        sector: "semantic" as MemorySector,
        tags: "",
    });
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Delete state
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
    const [entryToDelete, setEntryToDelete] = useState<string | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);

    // Agent data
    const { data: agentData, isLoading: isLoadingAgent } = useAgentDetail(agentId || "");

    // Fetch memories
    const fetchMemories = useCallback(async () => {
        if (!agentId) return;
        setIsLoading(true);
        try {
            const params: Record<string, any> = { limit: 50, offset: 0 };
            if (selectedSector !== "all") {
                params.sector = selectedSector;
            }

            const response = await apiClient.get<{ data: MemoryListResponse }>(
                `/agents/${agentId}/knowledge-base/items`,
                { params }
            );

            // Filter by __source:memory tag to only show personal memories
            let items = response.data.data?.items || [];

            // If search query, filter locally
            if (searchQuery) {
                const query = searchQuery.toLowerCase();
                items = items.filter(
                    (m) =>
                        m.content.toLowerCase().includes(query) ||
                        m.tags.some((tag) => tag.toLowerCase().includes(query))
                );
            }

            setMemories(items);
            setTotal(response.data.data?.total || 0);
        } catch (error) {
            console.error("Failed to fetch memories:", error);
            toast.error(t("error_fetch_memories", "Failed to fetch memories"));
        } finally {
            setIsLoading(false);
        }
    }, [agentId, selectedSector, searchQuery, t]);

    useEffect(() => {
        fetchMemories();
    }, [fetchMemories]);

    // Handlers
    const handleAddMemory = () => {
        setEditingEntry(null);
        setFormData({ content: "", sector: "semantic", tags: "" });
        setIsDialogOpen(true);
    };

    const handleEditMemory = (entry: MemoryEntry) => {
        setEditingEntry(entry);
        setFormData({
            content: entry.content,
            sector: entry.primary_sector as MemorySector,
            tags: entry.tags.filter((t) => !t.startsWith("__")).join(", "),
        });
        setIsDialogOpen(true);
    };

    const handleDeleteMemory = (entryId: string) => {
        setEntryToDelete(entryId);
        setDeleteConfirmOpen(true);
    };

    const handleConfirmDelete = async () => {
        if (!entryToDelete || !agentId) return;
        setIsDeleting(true);
        try {
            await apiClient.delete(`/agents/${agentId}/knowledge-base/items/${entryToDelete}`);
            toast.success(t("memory_deleted", "Memory deleted"));
            fetchMemories();
        } catch (error) {
            console.error("Failed to delete memory:", error);
            toast.error(t("error_delete_memory", "Failed to delete memory"));
        } finally {
            setIsDeleting(false);
            setDeleteConfirmOpen(false);
            setEntryToDelete(null);
        }
    };

    const handleSubmit = async () => {
        if (!agentId || !formData.content.trim()) return;
        setIsSubmitting(true);

        try {
            const tags = formData.tags
                .split(",")
                .map((t) => t.trim())
                .filter((t) => t);

            if (editingEntry) {
                // Update existing
                await apiClient.patch(`/agents/${agentId}/knowledge-base/items/${editingEntry.id}`, {
                    content: formData.content,
                    tags,
                });
                toast.success(t("memory_updated", "Memory updated"));
            } else {
                // Create new - add __source:memory tag to distinguish from knowledge base
                await apiClient.post(`/agents/${agentId}/knowledge-base/items`, {
                    content: formData.content,
                    sector: formData.sector,
                    tags: [...tags, "__source:memory"],
                });
                toast.success(t("memory_added", "Memory added"));
            }

            setIsDialogOpen(false);
            fetchMemories();
        } catch (error) {
            console.error("Failed to save memory:", error);
            toast.error(t("error_save_memory", "Failed to save memory"));
        } finally {
            setIsSubmitting(false);
        }
    };

    const getSectorColor = (sector: string) => {
        const colors: Record<string, string> = {
            personal: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
            semantic: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
            procedural: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
            episodic: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
        };
        return colors[sector] || "bg-gray-100 text-gray-800";
    };

    // Error state
    if (!agentId) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
                    <h2 className="text-lg font-semibold mb-2">{t("invalid_agent_id")}</h2>
                    <Button onClick={() => navigate("/agents")} variant="outline">
                        {t("back_to_agents")}
                    </Button>
                </div>
            </div>
        );
    }

    // Loading state
    if (isLoadingAgent) {
        return (
            <div className="p-6 space-y-6">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-9 w-9" />
                    <Skeleton className="h-8 w-64" />
                </div>
                <Skeleton className="h-10 w-full" />
                <div className="space-y-3">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <Skeleton key={i} className="h-24 w-full" />
                    ))}
                </div>
            </div>
        );
    }

    const agentName = agentData?.agent?.agent_name || t("agent");

    return (
        <>
            <PageHead
                title={`${agentName} - Bộ Nhớ`}
                description="Quản lý thông tin cá nhân mà AI nhớ về bạn"
            />

            <div className="p-6 space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => navigate(`/agents/${agentId}`)}
                        >
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                        <div className="flex items-center gap-2">
                            <Brain className="h-5 w-5 text-primary" />
                            <div>
                                <h1 className="text-xl font-semibold">{t("memory_title", "Bộ Nhớ")}</h1>
                                <p className="text-sm text-muted-foreground">{agentName}</p>
                            </div>
                        </div>
                    </div>
                    <Button onClick={handleAddMemory}>
                        <Plus className="h-4 w-4 mr-2" />
                        {t("add_memory", "Thêm Bộ Nhớ")}
                    </Button>
                </div>

                {/* Info Banner */}
                <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                    <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                            <Brain className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                            <div>
                                <p className="text-sm text-blue-800 dark:text-blue-200">
                                    <strong>Bộ Nhớ</strong> lưu trữ thông tin cá nhân mà AI ghi nhớ về bạn.
                                    Ví dụ: "Tôi có 2 con chó", "Tôi thích màu xanh".
                                </p>
                                <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                                    Khác với <strong>Cơ Sở Tri Thức</strong> dùng để upload tài liệu (PDF, DOCX).
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Search & Filter */}
                <div className="flex flex-wrap items-center gap-3">
                    <div className="relative flex-1 min-w-[200px]">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder={t("search_memories", "Tìm kiếm bộ nhớ...")}
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9"
                        />
                    </div>
                    <Select value={selectedSector} onValueChange={(v) => setSelectedSector(v as any)}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Lọc theo loại" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">Tất cả</SelectItem>
                            {SECTORS.map((s) => (
                                <SelectItem key={s.value} value={s.value}>
                                    {s.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>

                {/* Stats */}
                <div className="text-sm text-muted-foreground">
                    {t("memory_count", { count: memories.length, total: total })}
                </div>

                {/* Memory List */}
                {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    </div>
                ) : memories.length === 0 ? (
                    <Card className="py-12">
                        <CardContent className="flex flex-col items-center justify-center text-center">
                            <Brain className="h-12 w-12 text-muted-foreground/50 mb-4" />
                            <h3 className="text-lg font-medium mb-2">
                                {t("no_memories", "Chưa có bộ nhớ nào")}
                            </h3>
                            <p className="text-sm text-muted-foreground mb-4">
                                {t("no_memories_desc", "Bắt đầu cuộc trò chuyện để xây dựng bộ nhớ.")}
                            </p>
                            <Button onClick={handleAddMemory} variant="outline">
                                <Plus className="h-4 w-4 mr-2" />
                                {t("add_first_memory", "Thêm bộ nhớ đầu tiên")}
                            </Button>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid gap-3">
                        {memories.map((memory) => (
                            <Card key={memory.id} className="group hover:shadow-md transition-shadow">
                                <CardContent className="p-4">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-2">
                                                <Badge className={getSectorColor(memory.primary_sector)}>
                                                    {memory.primary_sector}
                                                </Badge>
                                                {memory.tags
                                                    .filter((t) => !t.startsWith("__"))
                                                    .slice(0, 3)
                                                    .map((tag) => (
                                                        <Badge key={tag} variant="outline" className="text-xs">
                                                            {tag}
                                                        </Badge>
                                                    ))}
                                            </div>
                                            <p className="text-sm">{memory.content}</p>
                                            <p className="text-xs text-muted-foreground mt-2">
                                                {new Date(memory.created_at).toLocaleDateString("vi-VN")}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleEditMemory(memory)}
                                            >
                                                <Edit2 className="h-4 w-4" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleDeleteMemory(memory.id)}
                                                className="text-destructive hover:text-destructive"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                )}

                {/* Add/Edit Dialog */}
                <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>
                                {editingEntry ? t("edit_memory", "Sửa bộ nhớ") : t("add_memory", "Thêm bộ nhớ")}
                            </DialogTitle>
                            <DialogDescription>
                                Lưu thông tin cá nhân để AI nhớ về bạn.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label>{t("content", "Nội dung")}</Label>
                                <Textarea
                                    placeholder="Ví dụ: Tôi có 2 con chó tên Tom và Jerry"
                                    value={formData.content}
                                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                    rows={3}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>{t("sector", "Loại")}</Label>
                                <Select
                                    value={formData.sector}
                                    onValueChange={(v) => setFormData({ ...formData, sector: v as MemorySector })}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Chọn lĩnh vực" />
                                    </SelectTrigger>
                                    <SelectContent position="popper" className="z-[9999]">
                                        {SECTORS.map((s) => (
                                            <SelectItem key={s.value} value={s.value}>
                                                {s.label} - {s.description}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label>{t("tags", "Tags")} (optional)</Label>
                                <Input
                                    placeholder="pet, family, hobby (phân cách bằng dấu phẩy)"
                                    value={formData.tags}
                                    onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                                {t("cancel", "Hủy")}
                            </Button>
                            <Button onClick={handleSubmit} disabled={isSubmitting || !formData.content.trim()}>
                                {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                                {t("save", "Lưu")}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                {/* Delete Confirmation */}
                <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>{t("delete_memory_confirm", "Xóa bộ nhớ?")}</AlertDialogTitle>
                            <AlertDialogDescription>
                                {t("delete_memory_desc", "Hành động này không thể hoàn tác.")}
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <div className="flex justify-end gap-2">
                            <AlertDialogCancel>{t("cancel", "Hủy")}</AlertDialogCancel>
                            <AlertDialogAction
                                onClick={handleConfirmDelete}
                                disabled={isDeleting}
                                className="bg-destructive hover:bg-destructive/90"
                            >
                                {isDeleting ? t("deleting", "Đang xóa...") : t("delete", "Xóa")}
                            </AlertDialogAction>
                        </div>
                    </AlertDialogContent>
                </AlertDialog>
            </div>
        </>
    );
};

export default AgentMemoryPage;
