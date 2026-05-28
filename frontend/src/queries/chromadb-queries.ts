/**
 * ChromaDB Knowledge Base Queries
 * Lightweight vector database for text, Excel, and Google Sheets import
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/config/axios-instance";
import { CHROMADB_ENDPOINTS } from "@/lib/api/endpoints";
import { toast } from "sonner";

// ==================== Types ====================

interface ChromaDocument {
    id: string;
    title: string;
    content: string;
    source: string;
    type: string;
}

interface ChromaSearchResult {
    content: string;
    title: string;
    source: string;
    score: number;
    metadata?: Record<string, unknown>;
}

interface ChromaDocumentsResponse {
    documents: ChromaDocument[];
    total: number;
}

interface ChromaStatsResponse {
    agent_id: string;
    document_count: number;
    collection_name: string;
}

interface ChromaHealthResponse {
    status: string;
    service: string;
    persist_directory?: string;
    error?: string;
}

// ==================== Queries ====================

/**
 * Check ChromaDB health
 */
export const useChromaDBHealth = (agentId: string) => {
    return useQuery({
        queryKey: ["chromadb", "health", agentId],
        queryFn: async () => {
            const response = await api.get(CHROMADB_ENDPOINTS.HEALTH(agentId));
            return response.data?.data as ChromaHealthResponse;
        },
        enabled: !!agentId,
        staleTime: 30 * 1000,
    });
};

/**
 * List ChromaDB documents
 */
export const useChromaDBDocuments = (agentId: string) => {
    return useQuery({
        queryKey: ["chromadb", "documents", agentId],
        queryFn: async () => {
            const response = await api.get(CHROMADB_ENDPOINTS.DOCUMENTS(agentId));
            return response.data?.data as ChromaDocumentsResponse;
        },
        enabled: !!agentId,
        staleTime: 10 * 1000,
    });
};

/**
 * Get ChromaDB stats
 */
export const useChromaDBStats = (agentId: string) => {
    return useQuery({
        queryKey: ["chromadb", "stats", agentId],
        queryFn: async () => {
            const response = await api.get(CHROMADB_ENDPOINTS.STATS(agentId));
            return response.data?.data as ChromaStatsResponse;
        },
        enabled: !!agentId,
    });
};

// ==================== Mutations ====================

/**
 * Add text knowledge
 */
export const useAddTextKnowledge = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ title, content }: { title: string; content: string }) => {
            const response = await api.post(CHROMADB_ENDPOINTS.TEXT(agentId), {
                title,
                content,
            });
            return response.data;
        },
        onSuccess: (data) => {
            toast.success(data?.message || "Đã thêm kiến thức thành công");
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["chromadb", "stats", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể thêm kiến thức");
        },
    });
};

/**
 * Import Excel file
 */
export const useImportExcel = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append("file", file);

            const response = await api.post(CHROMADB_ENDPOINTS.IMPORT_EXCEL(agentId), formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            return response.data;
        },
        onSuccess: (data) => {
            toast.success(data?.message || "Đã import Excel thành công");
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["chromadb", "stats", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể import Excel");
        },
    });
};

/**
 * Import Google Sheets
 */
export const useImportGoogleSheets = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (url: string) => {
            const response = await api.post(CHROMADB_ENDPOINTS.IMPORT_SHEETS(agentId), {
                url,
            });
            return response.data;
        },
        onSuccess: (data) => {
            toast.success(data?.message || "Đã import từ Google Sheets thành công");
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["chromadb", "stats", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể import từ Google Sheets");
        },
    });
};

/**
 * Search knowledge
 */
export const useSearchChromaDB = (agentId: string) => {
    return useMutation({
        mutationFn: async ({ query, k = 5 }: { query: string; k?: number }) => {
            const response = await api.post(CHROMADB_ENDPOINTS.SEARCH(agentId), {
                query,
                k,
            });
            return response.data?.data as {
                query: string;
                chunks: ChromaSearchResult[];
                total: number;
            };
        },
    });
};

/**
 * Delete a document
 */
export const useDeleteChromaDocument = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (docId: string) => {
            const response = await api.delete(CHROMADB_ENDPOINTS.DOCUMENT_DETAIL(agentId, docId));
            return response.data;
        },
        onSuccess: () => {
            toast.success("Đã xóa tài liệu");
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["chromadb", "stats", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể xóa tài liệu");
        },
    });
};

/**
 * Delete all knowledge
 */
export const useDeleteAllChromaKnowledge = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async () => {
            const response = await api.delete(CHROMADB_ENDPOINTS.DELETE_ALL(agentId));
            return response.data;
        },
        onSuccess: () => {
            toast.success("Đã xóa toàn bộ kiến thức");
            queryClient.invalidateQueries({ queryKey: ["chromadb", "documents", agentId] });
            queryClient.invalidateQueries({ queryKey: ["chromadb", "stats", agentId] });
        },
        onError: (error: any) => {
            toast.error(error?.response?.data?.detail || "Không thể xóa kiến thức");
        },
    });
};
