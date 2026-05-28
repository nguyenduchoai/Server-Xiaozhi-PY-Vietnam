/**
 * Unified Knowledge Base Queries
 * Smart router that auto-selects between RAGFlow and ChromaDB
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/config/axios-instance";
import { toast } from "sonner";

// ==================== Endpoints ====================

const ENDPOINTS = {
    HEALTH: (agentId: string) => `/agents/${agentId}/knowledge/health`,
    TEXT: (agentId: string) => `/agents/${agentId}/knowledge/text`,
    UPLOAD: (agentId: string) => `/agents/${agentId}/knowledge/upload`,
    IMPORT_SHEETS: (agentId: string) => `/agents/${agentId}/knowledge/import/sheets`,
    SEARCH: (agentId: string) => `/agents/${agentId}/knowledge/search`,
    DOCUMENTS: (agentId: string) => `/agents/${agentId}/knowledge/documents`,
    DOCUMENT_DETAIL: (agentId: string, docId: string) =>
        `/agents/${agentId}/knowledge/documents/${docId}`,
    DOCUMENT_CHUNKS: (agentId: string, docId: string) =>
        `/agents/${agentId}/knowledge/documents/${docId}/chunks`,
    CHUNKS: (agentId: string) => `/agents/${agentId}/knowledge/chunks`,
    CHUNK_DETAIL: (agentId: string, chunkId: string) =>
        `/agents/${agentId}/knowledge/chunks/${chunkId}`,
    STATS: (agentId: string) => `/agents/${agentId}/knowledge/stats`,
};

// ==================== Types ====================

interface KnowledgeDocument {
    id: string;
    title?: string;
    content?: string;
    source?: string;
    type?: string;
    backend: "ragflow" | "chromadb";
}

interface KnowledgeSearchResult {
    content: string;
    title?: string;
    source?: string;
    score: number;
    backend: "ragflow" | "chromadb";
}

interface BackendHealth {
    ragflow: boolean;
    chromadb: boolean;
}

interface HealthResponse {
    status: string;
    backends: BackendHealth;
    message: string;
}

interface DocumentsResponse {
    documents: KnowledgeDocument[];
    total: number;
}

interface SearchResponse {
    query: string;
    chunks: KnowledgeSearchResult[];
    total: number;
    backends_searched: string[];
}

interface StatsResponse {
    agent_id: string;
    backends: Record<string, unknown>;
    total_documents: number;
}

interface UploadResult {
    backend: string;
    input_type?: string;
    filename?: string;
    added?: number;
    document_id?: string;
    status: string;
}

// ==================== Queries ====================

/**
 * Check unified knowledge health
 */
export const useUnifiedKnowledgeHealth = (agentId: string) => {
    return useQuery({
        queryKey: ["knowledge-unified", "health", agentId],
        queryFn: async () => {
            const response = await api.get(ENDPOINTS.HEALTH(agentId));
            return response.data?.data as HealthResponse;
        },
        enabled: !!agentId,
        staleTime: 30 * 1000,
    });
};

/**
 * List all documents from all backends
 */
export const useUnifiedDocuments = (agentId: string) => {
    return useQuery({
        queryKey: ["knowledge-unified", "documents", agentId],
        queryFn: async () => {
            const response = await api.get(ENDPOINTS.DOCUMENTS(agentId));
            return response.data?.data as DocumentsResponse;
        },
        enabled: !!agentId,
        staleTime: 10 * 1000,
    });
};

/**
 * Get unified stats
 */
export const useUnifiedStats = (agentId: string) => {
    return useQuery({
        queryKey: ["knowledge-unified", "stats", agentId],
        queryFn: async () => {
            const response = await api.get(ENDPOINTS.STATS(agentId));
            return response.data?.data as StatsResponse;
        },
        enabled: !!agentId,
    });
};

// ==================== Mutations ====================

/**
 * Add text knowledge (auto-routed)
 */
export const useAddUnifiedText = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            title,
            content,
            backend = "auto",
            image_url,
        }: {
            title: string;
            content: string;
            backend?: "auto" | "ragflow" | "chromadb";
            image_url?: string;
        }) => {
            const response = await api.post(ENDPOINTS.TEXT(agentId), {
                title,
                content,
                backend,
                image_url,
            });
            return response.data;
        },
        onSuccess: (data) => {
            toast.success(data?.message || "Đã thêm kiến thức thành công");
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "stats", agentId] });
            // Also invalidate specific backend caches
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["ragflow", "documents", agentId] });
            // Invalidate all-chunks for the knowledge list
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "all-chunks", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể thêm kiến thức");
        },
    });
};

/**
 * Upload file (auto-routed based on file type)
 */
export const useUploadUnifiedFile = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ file, backend = "auto" }: { file: File; backend?: string }) => {
            const formData = new FormData();
            formData.append("file", file);

            const response = await api.post(
                `${ENDPOINTS.UPLOAD(agentId)}?backend=${backend}`,
                formData,
                {
                    headers: { "Content-Type": "multipart/form-data" },
                }
            );
            return response.data?.data as UploadResult;
        },
        onSuccess: (data) => {
            const backendName = data?.backend === "ragflow" ? "RAGFlow" : "ChromaDB";
            toast.success(`Đã upload vào ${backendName}`);
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "stats", agentId] });
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["ragflow", "documents", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể upload file");
        },
    });
};

/**
 * Import Google Sheets
 */
export const useImportUnifiedSheets = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (url: string) => {
            const response = await api.post(ENDPOINTS.IMPORT_SHEETS(agentId), { url });
            return response.data;
        },
        onSuccess: (data) => {
            toast.success(data?.message || "Đã import từ Google Sheets");
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "stats", agentId] });
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể import");
        },
    });
};

/**
 * Search across all backends
 */
export const useUnifiedSearch = (agentId: string) => {
    return useMutation({
        mutationFn: async ({
            query,
            k = 5,
            search_all = true,
        }: {
            query: string;
            k?: number;
            search_all?: boolean;
        }) => {
            const response = await api.post(ENDPOINTS.SEARCH(agentId), {
                query,
                k,
                search_all,
            });
            return response.data?.data as SearchResponse;
        },
    });
};

/**
 * Delete a document
 */
export const useDeleteUnifiedDocument = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ docId, backend }: { docId: string; backend?: string }) => {
            const url = backend
                ? `${ENDPOINTS.DOCUMENT_DETAIL(agentId, docId)}?backend=${backend}`
                : ENDPOINTS.DOCUMENT_DETAIL(agentId, docId);
            const response = await api.delete(url);
            return response.data;
        },
        onSuccess: () => {
            toast.success("Đã xóa tài liệu");
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "stats", agentId] });
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["ragflow", "documents", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể xóa");
        },
    });
};

// ==================== Document Chunks ====================

interface Chunk {
    id: string;
    content: string;
    document_id: string;
}

interface ChunksResponse {
    chunks: Chunk[];
    total: number;
    page: number;
    page_size: number;
}

/**
 * Get chunks from a RAGFlow document
 */
export const useDocumentChunks = (agentId: string, docId: string | null, page = 1, pageSize = 50) => {
    return useQuery({
        queryKey: ["knowledge-unified", "chunks", agentId, docId, page, pageSize],
        queryFn: async () => {
            if (!docId) return null;
            const response = await api.get(
                `${ENDPOINTS.DOCUMENT_CHUNKS(agentId, docId)}?page=${page}&page_size=${pageSize}`
            );
            return response.data?.data as ChunksResponse;
        },
        enabled: !!docId && !!agentId,
    });
};

// ==================== ChromaDB Chunks Management ====================

interface KnowledgeChunk {
    id: string;
    title: string;
    content: string;
    source?: string;
    type?: string;
}

interface AllChunksResponse {
    chunks: KnowledgeChunk[];
    total: number;
}

/**
 * List all ChromaDB chunks for editing
 */
export const useAllChunks = (agentId: string) => {
    return useQuery({
        queryKey: ["knowledge-unified", "all-chunks", agentId],
        queryFn: async () => {
            const response = await api.get(ENDPOINTS.CHUNKS(agentId));
            return response.data?.data as AllChunksResponse;
        },
        enabled: !!agentId,
    });
};

/**
 * Update a ChromaDB chunk
 */
export const useUpdateChunk = (agentId: string) => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ chunkId, content, title }: { chunkId: string; content: string; title?: string }) => {
            const response = await api.put(ENDPOINTS.CHUNK_DETAIL(agentId, chunkId), { content, title });
            return response.data;
        },
        onSuccess: () => {
            toast.success("Đã cập nhật nội dung");
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "all-chunks", agentId] });
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "documents", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể cập nhật");
        },
    });
};

/**
 * Delete a ChromaDB chunk
 */
export const useDeleteChunk = (agentId: string) => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (chunkId: string) => {
            const response = await api.delete(ENDPOINTS.CHUNK_DETAIL(agentId, chunkId));
            return response.data;
        },
        onSuccess: () => {
            toast.success("Đã xóa chunk");
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "all-chunks", agentId] });
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["knowledge-unified", "stats", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể xóa");
        },
    });
};
