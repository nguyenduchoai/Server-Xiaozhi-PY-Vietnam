/**
 * Agent Knowledge Base Page V2 - Unified Knowledge Storage
 * 
 * Features:
 * - Upload Document (PDF, DOCX, TXT, Excel, etc.) - Auto-routed to RAGFlow or ChromaDB
 * - Import from Google Sheets
 * - Add Text Knowledge manually
 * - Search across all backends
 * - Unified document management
 */

import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
    AlertCircle, ArrowLeft, FileText, Upload, Search,
    Trash2, Loader2, FileUp, Link2, FileSpreadsheet,
    PenLine, Eye, Edit2, ImagePlus, X
} from "lucide-react";
import { toast } from "sonner";
import api from "@/config/axios-instance";

import { useAgentDetail } from "@/queries/agent-queries";
import {
    useUnifiedKnowledgeHealth,
    useUnifiedDocuments,
    useAddUnifiedText,
    useUploadUnifiedFile,
    useImportUnifiedSheets,
    useUnifiedSearch,
    useDeleteUnifiedDocument,
    useDocumentChunks,
    useAllChunks,
    useUpdateChunk,
    useDeleteChunk,
} from "@/queries/knowledge-unified-queries";
import { PageHead } from "@/components/PageHead";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
// Dropdown menu - for future use
// import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

// Accepted file types
const ACCEPTED_TYPES = [
    ".pdf", ".doc", ".docx", ".txt", ".md", ".html", ".csv", ".xlsx", ".xls",
];

export const AgentKnowledgePageV2 = () => {
    const { agentId } = useParams<{ agentId: string }>();
    const navigate = useNavigate();
    useTranslation("agents"); // Keep for future i18n

    // State
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<any[] | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
    const [docToDelete, setDocToDelete] = useState<string | null>(null);
    const [docBackend, setDocBackend] = useState<string | null>(null);

    // Modal states
    const [textModalOpen, setTextModalOpen] = useState(false);
    const [sheetsModalOpen, setSheetsModalOpen] = useState(false);
    const [textTitle, setTextTitle] = useState("");
    const [textContent, setTextContent] = useState("");
    const [sheetsUrl, setSheetsUrl] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Chunks modal state
    const [chunksModalOpen, setChunksModalOpen] = useState(false);
    const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
    const [selectedDocName, setSelectedDocName] = useState<string>("");

    // Edit chunk modal state
    const [editChunkModalOpen, setEditChunkModalOpen] = useState(false);
    const [editingChunk, setEditingChunk] = useState<{ id: string; title: string; content: string } | null>(null);
    const [editContent, setEditContent] = useState("");
    const [editTitle, setEditTitle] = useState("");

    // Image upload state for text knowledge
    const [textImageUrl, setTextImageUrl] = useState<string | null>(null);
    const [isUploadingImage, setIsUploadingImage] = useState(false);

    // Queries
    const { data: agentData, isLoading: isLoadingAgent, error: agentError } = useAgentDetail(agentId || "");
    const { data: healthData, isLoading: isLoadingHealth, error: healthError } = useUnifiedKnowledgeHealth(agentId || "");
    const { data: documentsData, isLoading: isLoadingDocs } =
        useUnifiedDocuments(agentId || "");

    // Chunks query
    const { data: chunksData, isLoading: isLoadingChunks } = useDocumentChunks(
        agentId || "",
        selectedDocId
    );

    // All ChromaDB chunks for editing
    const { data: allChunksData, isLoading: isLoadingAllChunks } = useAllChunks(agentId || "");

    // Mutations
    const textMutation = useAddUnifiedText(agentId || "");
    const uploadMutation = useUploadUnifiedFile(agentId || "");
    const sheetsMutation = useImportUnifiedSheets(agentId || "");
    const searchMutation = useUnifiedSearch(agentId || "");
    const deleteMutation = useDeleteUnifiedDocument(agentId || "");
    const updateChunkMutation = useUpdateChunk(agentId || "");
    const deleteChunkMutation = useDeleteChunk(agentId || "");

    // Handlers
    const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const extension = "." + file.name.split(".").pop()?.toLowerCase();

        if (!ACCEPTED_TYPES.includes(extension)) {
            toast.error(`Định dạng không hỗ trợ. Chấp nhận: ${ACCEPTED_TYPES.join(", ")}`);
            return;
        }

        if (file.size > 50 * 1024 * 1024) {
            toast.error("File quá lớn. Tối đa 50MB");
            return;
        }

        setIsUploading(true);
        try {
            // Use unified upload - auto-routes based on file type
            await uploadMutation.mutateAsync({ file });
        } catch {
            // Error handled by mutation
        } finally {
            setIsUploading(false);
            event.target.value = "";
        }
    }, [uploadMutation]);

    const handleSearch = useCallback(async () => {
        if (!searchQuery.trim()) {
            setSearchResults(null);
            return;
        }
        try {
            const result = await searchMutation.mutateAsync({ query: searchQuery, k: 5 });
            setSearchResults(result?.chunks || []);
        } catch {
            setSearchResults([]);
        }
    }, [searchQuery, searchMutation]);

    const handleDeleteDoc = (docId: string, backend?: string) => {
        setDocToDelete(docId);
        setDocBackend(backend || null);
        setDeleteConfirmOpen(true);
    };

    const handleConfirmDelete = async () => {
        if (!docToDelete) return;
        await deleteMutation.mutateAsync({ docId: docToDelete, backend: docBackend || undefined });
        setDeleteConfirmOpen(false);
        setDocToDelete(null);
        setDocBackend(null);
    };

    const handleAddText = async () => {
        if (!textTitle.trim() || !textContent.trim()) {
            toast.error("Vui lòng nhập tiêu đề và nội dung");
            return;
        }
        setIsSubmitting(true);
        try {
            await textMutation.mutateAsync({
                title: textTitle,
                content: textContent,
                image_url: textImageUrl || undefined,
            });
            toast.success("Đã thêm kiến thức thành công!");
            setTextModalOpen(false);
            setTextTitle("");
            setTextContent("");
            setTextImageUrl(null);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Upload image for knowledge entry
    const handleImageUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        if (!file.type.startsWith("image/")) {
            toast.error("Vui lòng chọn file ảnh");
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            toast.error("File quá lớn (max 10MB)");
            return;
        }

        setIsUploadingImage(true);
        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await api.post(
                `/agents/${agentId}/knowledge/upload-image`,
                formData,
                { headers: { "Content-Type": "multipart/form-data" } }
            );

            const imageUrl = response.data?.data?.url;
            if (imageUrl) {
                setTextImageUrl(imageUrl);
                toast.success("Đã upload hình ảnh");
            }
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Không thể upload hình");
        } finally {
            setIsUploadingImage(false);
            event.target.value = "";
        }
    }, [agentId]);

    const handleImportSheets = async () => {
        if (!sheetsUrl.trim()) {
            toast.error("Vui lòng nhập link Google Sheets");
            return;
        }

        // Extract sheet ID from URL
        const match = sheetsUrl.match(/\/d\/([a-zA-Z0-9-_]+)/);
        if (!match) {
            toast.error("Link Google Sheets không hợp lệ");
            return;
        }

        setIsSubmitting(true);
        try {
            await sheetsMutation.mutateAsync(sheetsUrl);
            setSheetsModalOpen(false);
            setSheetsUrl("");
        } finally {
            setIsSubmitting(false);
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    };

    const getStatusBadge = (status: string) => {
        const statusLower = status?.toLowerCase();
        if (["parsed", "done", "1"].includes(statusLower)) {
            return <Badge className="bg-green-100 text-green-800">Đã xử lý</Badge>;
        }
        if (["parsing", "processing", "0"].includes(statusLower)) {
            return <Badge className="bg-yellow-100 text-yellow-800">Đang xử lý</Badge>;
        }
        if (statusLower === "failed") {
            return <Badge className="bg-red-100 text-red-800">Lỗi</Badge>;
        }
        return <Badge variant="outline">{status}</Badge>;
    };

    // Error state
    if (!agentId) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
                    <h2 className="text-lg font-semibold mb-2">Agent ID không hợp lệ</h2>
                    <Button onClick={() => navigate("/agents")} variant="outline">
                        Quay lại danh sách
                    </Button>
                </div>
            </div>
        );
    }

    // Handle query errors gracefully
    if (agentError || healthError) {
        console.error("Knowledge page error:", { agentError, healthError });
        return (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <AlertCircle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
                    <h2 className="text-lg font-semibold mb-2">Không thể tải dữ liệu</h2>
                    <p className="text-muted-foreground mb-4">Vui lòng thử lại sau</p>
                    <div className="flex gap-2 justify-center">
                        <Button onClick={() => window.location.reload()} variant="outline">
                            Tải lại
                        </Button>
                        <Button onClick={() => navigate(`/agents/${agentId}`)} variant="outline">
                            Quay lại Agent
                        </Button>
                    </div>
                </div>
            </div>
        );
    }

    // Loading state
    if (isLoadingAgent || isLoadingHealth) {
        return (
            <div className="p-6 space-y-6">
                <div className="flex items-center gap-4">
                    <Skeleton className="h-9 w-9" />
                    <Skeleton className="h-8 w-64" />
                </div>
                <div className="flex gap-2">
                    <Skeleton className="h-10 w-32" />
                    <Skeleton className="h-10 w-32" />
                    <Skeleton className="h-10 w-32" />
                </div>
                <Skeleton className="h-10 w-full" />
                <div className="space-y-3">
                    {Array.from({ length: 3 }).map((_, i) => (
                        <Skeleton key={i} className="h-20 w-full" />
                    ))}
                </div>
            </div>
        );
    }

    const agentName = agentData?.agent?.agent_name || "Agent";
    const isChromaDBAvailable = healthData?.status === "healthy";
    const documents = documentsData?.documents || [];

    return (
        <>
            <PageHead
                title={`${agentName} - Cơ Sở Tri Thức`}
                description="Upload và quản lý tài liệu cho AI"
            />

            <div className="p-6 space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between gap-4 flex-wrap">
                    <div className="flex items-center gap-3">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => navigate(`/agents/${agentId}`)}
                        >
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                        <div className="flex items-center gap-2">
                            <FileText className="h-5 w-5 text-primary" />
                            <div>
                                <h1 className="text-xl font-semibold">Cơ Sở Tri Thức</h1>
                                <p className="text-sm text-muted-foreground">{agentName}</p>
                            </div>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 flex-wrap">
                        {/* Upload Document */}
                        <label className="cursor-pointer">
                            <input
                                type="file"
                                accept={ACCEPTED_TYPES.join(",")}
                                onChange={handleFileUpload}
                                className="hidden"
                                disabled={isUploading || !isChromaDBAvailable}
                            />
                            <Button
                                disabled={isUploading || !isChromaDBAvailable}
                                asChild
                                className="bg-blue-600 hover:bg-blue-700"
                            >
                                <span>
                                    {isUploading ? (
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    ) : (
                                        <Upload className="h-4 w-4 mr-2" />
                                    )}
                                    Upload Document
                                </span>
                            </Button>
                        </label>

                        {/* Import CSV */}
                        <label className="cursor-pointer">
                            <input
                                type="file"
                                accept=".csv"
                                onChange={handleFileUpload}
                                className="hidden"
                                disabled={isUploading || !isChromaDBAvailable}
                            />
                            <Button
                                variant="outline"
                                disabled={isUploading || !isChromaDBAvailable}
                                asChild
                            >
                                <span>
                                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                                    Nhập CSV
                                </span>
                            </Button>
                        </label>

                        {/* Import Google Sheets */}
                        <Button
                            variant="outline"
                            onClick={() => setSheetsModalOpen(true)}
                            disabled={!isChromaDBAvailable}
                            className="border-green-500 text-green-600 hover:bg-green-50"
                        >
                            <Link2 className="h-4 w-4 mr-2" />
                            Nhập từ Google Sheets
                        </Button>

                        {/* Add Text Knowledge */}
                        <Button
                            onClick={() => setTextModalOpen(true)}
                            disabled={!isChromaDBAvailable}
                            className="bg-orange-500 hover:bg-orange-600"
                        >
                            <PenLine className="h-4 w-4 mr-2" />
                            Thêm Kiến Thức
                        </Button>

                        {/* Delete All (danger) */}
                        {documents.length > 0 && (
                            <Button
                                variant="destructive"
                                onClick={() => toast.info("Tính năng xóa tất cả đang phát triển")}
                            >
                                <Trash2 className="h-4 w-4 mr-2" />
                                Xóa Dữ Liệu
                            </Button>
                        )}
                    </div>
                </div>

                {/* Info Card */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            Giới Thiệu Knowledge
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label className="text-xs text-muted-foreground">Tên</Label>
                                <p className="font-medium">{agentName}</p>
                            </div>
                            <div>
                                <Label className="text-xs text-muted-foreground">Tên Model</Label>
                                <p className="text-muted-foreground">RAGFlow (text-embedding-3-small)</p>
                            </div>
                        </div>
                        <div>
                            <Label className="text-xs text-muted-foreground">Mô Tả</Label>
                            <p className="text-sm text-muted-foreground">
                                Cơ sở tri thức dùng để lưu trữ tài liệu (PDF, DOCX, TXT...).
                                AI sẽ tìm kiếm trong tài liệu để trả lời câu hỏi.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Search */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base">Tìm kiếm dữ liệu...</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-2">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Tìm kiếm trong tài liệu..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                                    className="pl-9"
                                />
                            </div>
                            <Button
                                onClick={handleSearch}
                                disabled={searchMutation.isPending || !searchQuery.trim()}
                                className="bg-blue-600 hover:bg-blue-700"
                            >
                                {searchMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                                <Search className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* Search Results */}
                        {searchResults && searchResults.length > 0 && (
                            <div className="mt-4 space-y-2">
                                <h4 className="font-medium text-sm">Kết quả ({searchResults.length}):</h4>
                                {searchResults.map((result, idx) => (
                                    <div key={idx} className="p-3 bg-muted rounded-lg text-sm">
                                        <p>{result.content}</p>
                                        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                                            <Badge variant="outline">{result.source || result.document_name}</Badge>
                                            {result.score && <span>Score: {(result.score * 100).toFixed(1)}%</span>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {searchResults && searchResults.length === 0 && (
                            <p className="mt-4 text-sm text-muted-foreground text-center">
                                Không tìm thấy kết quả
                            </p>
                        )}
                    </CardContent>
                </Card>

                {/* Document List */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-base">
                            Tài Liệu Đã Tải Lên ({documents.length})
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {isLoadingDocs ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                            </div>
                        ) : documents.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <FileUp className="h-12 w-12 text-muted-foreground/50 mb-4" />
                                <p className="text-muted-foreground">
                                    Chưa có tài liệu nào được tải lên
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {documents.map((doc: any) => (
                                    <div
                                        key={doc.id}
                                        className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors group"
                                    >
                                        <div className="flex items-center gap-3 flex-1 min-w-0">
                                            <FileText className="h-5 w-5 text-blue-500 flex-shrink-0" />
                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium truncate">{doc.name}</p>
                                                <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                                                    {getStatusBadge(doc.status)}
                                                    {doc.size && <span>{formatFileSize(doc.size)}</span>}
                                                    {doc.chunk_count > 0 && <span>{doc.chunk_count} chunks</span>}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            {/* View chunks button - only for RAGFlow docs with chunks */}
                                            {doc.backend === "ragflow" && doc.chunk_count > 0 && (
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => {
                                                        setSelectedDocId(doc.id);
                                                        setSelectedDocName(doc.name || "Document");
                                                        setChunksModalOpen(true);
                                                    }}
                                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                                    title="Xem chunks"
                                                >
                                                    <Eye className="h-4 w-4" />
                                                </Button>
                                            )}
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                onClick={() => handleDeleteDoc(doc.id, doc.backend)}
                                                className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive hover:bg-destructive/10"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* ChromaDB Chunks List - Editable */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base flex items-center justify-between">
                            <span>Kiến Thức Đã Nhập ({allChunksData?.total || 0})</span>
                            {isLoadingAllChunks && <Loader2 className="h-4 w-4 animate-spin" />}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {isLoadingAllChunks ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                            </div>
                        ) : !allChunksData?.chunks || allChunksData.chunks.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <FileText className="h-12 w-12 text-muted-foreground/50 mb-4" />
                                <p className="text-muted-foreground">
                                    Chưa có kiến thức nào. Import từ Google Sheets hoặc thêm thủ công.
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {allChunksData.chunks.map((chunk) => (
                                    <div
                                        key={chunk.id}
                                        className="p-4 bg-muted/50 rounded-lg border border-border/50 group hover:border-primary/30 transition-colors"
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium text-sm mb-1 truncate">
                                                    {chunk.title || "Untitled"}
                                                </p>
                                                <p className="text-sm text-muted-foreground line-clamp-3 whitespace-pre-wrap">
                                                    {chunk.content}
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-1 flex-shrink-0">
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => {
                                                        setEditingChunk(chunk);
                                                        setEditTitle(chunk.title || "");
                                                        setEditContent(chunk.content || "");
                                                        setEditChunkModalOpen(true);
                                                    }}
                                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                                                    title="Sửa"
                                                >
                                                    <Edit2 className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    onClick={() => {
                                                        if (confirm("Xóa chunk này?")) {
                                                            deleteChunkMutation.mutate(chunk.id);
                                                        }
                                                    }}
                                                    className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:text-destructive hover:bg-destructive/10"
                                                    title="Xóa"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Add Text Modal */}
            <Dialog open={textModalOpen} onOpenChange={(open) => {
                setTextModalOpen(open);
                if (!open) {
                    setTextImageUrl(null);
                }
            }}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Thêm Kiến Thức</DialogTitle>
                        <DialogDescription>
                            Nhập nội dung text để thêm vào cơ sở tri thức
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Tiêu đề</Label>
                            <Input
                                placeholder="Nhập tiêu đề..."
                                value={textTitle}
                                onChange={(e) => setTextTitle(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Nội dung</Label>
                            <Textarea
                                placeholder="Nhập nội dung kiến thức..."
                                value={textContent}
                                onChange={(e) => setTextContent(e.target.value)}
                                rows={6}
                            />
                        </div>

                        {/* Image Upload Section */}
                        <div className="space-y-2">
                            <Label className="flex items-center gap-2">
                                <ImagePlus className="h-4 w-4" />
                                Hình ảnh (Tùy chọn)
                            </Label>

                            {textImageUrl ? (
                                <div className="relative inline-block">
                                    <img
                                        src={textImageUrl}
                                        alt="Preview"
                                        className="max-w-[200px] max-h-[200px] rounded-lg border object-cover"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setTextImageUrl(null)}
                                        className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                                    >
                                        <X className="h-4 w-4" />
                                    </button>
                                </div>
                            ) : (
                                <div className="flex items-center gap-2">
                                    <input
                                        type="file"
                                        id="knowledge-image"
                                        accept="image/*"
                                        className="hidden"
                                        onChange={handleImageUpload}
                                    />
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={() => document.getElementById("knowledge-image")?.click()}
                                        disabled={isUploadingImage}
                                    >
                                        {isUploadingImage ? (
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        ) : (
                                            <ImagePlus className="h-4 w-4 mr-2" />
                                        )}
                                        Chọn ảnh
                                    </Button>
                                    <span className="text-xs text-muted-foreground">
                                        Max 800x800, tự động nén ≤500KB
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => {
                            setTextModalOpen(false);
                            setTextImageUrl(null);
                        }}>
                            Hủy
                        </Button>
                        <Button onClick={handleAddText} disabled={isSubmitting}>
                            {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                            Thêm
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Google Sheets Modal */}
            <Dialog open={sheetsModalOpen} onOpenChange={setSheetsModalOpen}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>Nhập từ Google Sheets</DialogTitle>
                        <DialogDescription>
                            Nhập link Google Sheets để import dữ liệu
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Link Google Sheets</Label>
                            <Input
                                placeholder="https://docs.google.com/spreadsheets/d/..."
                                value={sheetsUrl}
                                onChange={(e) => setSheetsUrl(e.target.value)}
                            />
                            <p className="text-xs text-muted-foreground">
                                Sheet phải được chia sẻ công khai hoặc có quyền "Anyone with link"
                            </p>
                        </div>

                        {/* Data Format Guide */}
                        <div className="bg-muted/50 p-3 rounded-lg space-y-2">
                            <p className="text-sm font-medium">📋 Định dạng dữ liệu khuyến nghị:</p>
                            <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                                <li><strong>Cột A:</strong> Câu hỏi / Tiêu đề</li>
                                <li><strong>Cột B:</strong> Câu trả lời / Nội dung</li>
                                <li><strong>Cột C:</strong> Danh mục (tùy chọn)</li>
                                <li><strong>Cột D:</strong> Ghi chú (tùy chọn)</li>
                            </ul>
                            <a
                                href="/templates/knowledge_template.csv"
                                download="knowledge_template.csv"
                                className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-2"
                            >
                                ⬇️ Tải file mẫu CSV
                            </a>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setSheetsModalOpen(false)}>
                            Hủy
                        </Button>
                        <Button onClick={handleImportSheets} disabled={isSubmitting}>
                            {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                            Import
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation */}
            <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Xóa tài liệu?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Tài liệu sẽ bị xóa vĩnh viễn khỏi cơ sở tri thức. Không thể hoàn tác.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <div className="flex justify-end gap-2">
                        <AlertDialogCancel>Hủy</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleConfirmDelete}
                            disabled={deleteMutation.isPending}
                            className="bg-destructive hover:bg-destructive/90"
                        >
                            {deleteMutation.isPending ? "Đang xóa..." : "Xóa"}
                        </AlertDialogAction>
                    </div>
                </AlertDialogContent>
            </AlertDialog>

            {/* Chunks Modal */}
            <Dialog open={chunksModalOpen} onOpenChange={(open) => {
                setChunksModalOpen(open);
                if (!open) {
                    setSelectedDocId(null);
                    setSelectedDocName("");
                }
            }}>
                <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <FileText className="h-5 w-5 text-blue-500" />
                            {selectedDocName}
                        </DialogTitle>
                        <DialogDescription>
                            Nội dung đã được xử lý và chia thành các đoạn (chunks)
                        </DialogDescription>
                    </DialogHeader>
                    <div className="flex-1 overflow-y-auto space-y-3 py-4 pr-2">
                        {isLoadingChunks ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                            </div>
                        ) : chunksData?.chunks && chunksData.chunks.length > 0 ? (
                            <>
                                <div className="text-sm text-muted-foreground mb-4">
                                    Tổng: {chunksData.total} chunks
                                </div>
                                {chunksData.chunks.map((chunk, index) => (
                                    <div
                                        key={chunk.id}
                                        className="p-4 bg-muted/50 rounded-lg border border-border/50"
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <Badge variant="outline" className="text-xs">
                                                #{index + 1}
                                            </Badge>
                                        </div>
                                        <p className="text-sm whitespace-pre-wrap leading-relaxed">
                                            {chunk.content}
                                        </p>
                                    </div>
                                ))}
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <AlertCircle className="h-12 w-12 text-muted-foreground/50 mb-4" />
                                <p className="text-muted-foreground">
                                    Không có chunks nào
                                </p>
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>

            {/* Edit Chunk Modal */}
            <Dialog open={editChunkModalOpen} onOpenChange={(open) => {
                setEditChunkModalOpen(open);
                if (!open) {
                    setEditingChunk(null);
                    setEditContent("");
                    setEditTitle("");
                }
            }}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <Edit2 className="h-5 w-5 text-blue-500" />
                            Sửa Kiến Thức
                        </DialogTitle>
                        <DialogDescription>
                            Chỉnh sửa nội dung kiến thức đã nhập
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="edit-title">Tiêu đề</Label>
                            <Input
                                id="edit-title"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                placeholder="Tiêu đề kiến thức..."
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="edit-content">Nội dung</Label>
                            <Textarea
                                id="edit-content"
                                value={editContent}
                                onChange={(e) => setEditContent(e.target.value)}
                                placeholder="Nội dung kiến thức..."
                                rows={10}
                                className="resize-none"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditChunkModalOpen(false)}>
                            Hủy
                        </Button>
                        <Button
                            onClick={() => {
                                if (editingChunk && editContent.trim()) {
                                    updateChunkMutation.mutate({
                                        chunkId: editingChunk.id,
                                        content: editContent.trim(),
                                        title: editTitle.trim() || undefined,
                                    });
                                    setEditChunkModalOpen(false);
                                }
                            }}
                            disabled={updateChunkMutation.isPending || !editContent.trim()}
                        >
                            {updateChunkMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                            Lưu
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
};

export default AgentKnowledgePageV2;
