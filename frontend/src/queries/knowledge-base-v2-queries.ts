/**
 * Knowledge Base V2 Queries (RAGFlow)
 * 
 * For document management (PDF, DOCX, etc.)
 * Uses RAGFlow backend for document processing and search.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import apiClient from "@/config/axios-instance";
import { KNOWLEDGE_BASE_V2_ENDPOINTS } from "@/lib/api/endpoints";

// Types
export interface RAGFlowDocument {
    id: string;
    name: string;
    size: number;
    type: string;
    status: string;
    chunk_count: number;
    create_time: string;
    update_time: string;
}

export interface RAGFlowDocumentList {
    documents: RAGFlowDocument[];
    total: number;
}

export interface RAGFlowSearchResult {
    chunks: {
        content: string;
        document_name: string;
        score: number;
    }[];
    total: number;
}

export interface RAGFlowHealthCheck {
    status: "healthy" | "degraded" | "unavailable";
    ragflow_available: boolean;
    message?: string;
}

// Query Keys
export const knowledgeBaseV2Keys = {
    all: ["knowledge-base-v2"] as const,
    health: (agentId: string) => [...knowledgeBaseV2Keys.all, "health", agentId] as const,
    documents: (agentId: string) => [...knowledgeBaseV2Keys.all, "documents", agentId] as const,
};

// Queries

/**
 * Check health status of RAGFlow knowledge base
 */
export const useKnowledgeBaseV2Health = (agentId: string, enabled = true) => {
    return useQuery<RAGFlowHealthCheck>({
        queryKey: knowledgeBaseV2Keys.health(agentId),
        queryFn: async () => {
            const { data } = await apiClient.get(KNOWLEDGE_BASE_V2_ENDPOINTS.HEALTH(agentId));
            return data.data;
        },
        enabled: Boolean(agentId) && enabled,
        staleTime: 30 * 1000, // 30 seconds
    });
};

/**
 * List documents in agent's knowledge base
 */
export const useKnowledgeBaseV2Documents = (agentId: string, enabled = true) => {
    return useQuery<RAGFlowDocumentList>({
        queryKey: knowledgeBaseV2Keys.documents(agentId),
        queryFn: async () => {
            const { data } = await apiClient.get(KNOWLEDGE_BASE_V2_ENDPOINTS.DOCUMENTS(agentId));
            return data.data;
        },
        enabled: Boolean(agentId) && enabled,
    });
};

// Mutations

/**
 * Upload document to RAGFlow knowledge base
 */
export const useUploadDocument = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append("file", file);

            const { data } = await apiClient.post(
                KNOWLEDGE_BASE_V2_ENDPOINTS.UPLOAD(agentId),
                formData,
                {
                    headers: {
                        "Content-Type": "multipart/form-data",
                    },
                }
            );
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseV2Keys.documents(agentId) });
            toast.success("Tài liệu đã được tải lên thành công");
        },
        onError: (error: any) => {
            const message = error.response?.data?.detail || "Không thể tải lên tài liệu";
            toast.error(message);
        },
    });
};

/**
 * Upload text content to RAGFlow knowledge base
 */
export const useUploadText = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (payload: { title: string; content: string }) => {
            const { data } = await apiClient.post(
                KNOWLEDGE_BASE_V2_ENDPOINTS.TEXT(agentId),
                payload
            );
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseV2Keys.documents(agentId) });
            toast.success("Nội dung đã được lưu thành công");
        },
        onError: (error: any) => {
            const message = error.response?.data?.detail || "Không thể lưu nội dung";
            toast.error(message);
        },
    });
};

/**
 * Delete document from RAGFlow knowledge base
 */
export const useDeleteDocument = (agentId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (documentId: string) => {
            const { data } = await apiClient.delete(
                KNOWLEDGE_BASE_V2_ENDPOINTS.DOCUMENT_DETAIL(agentId, documentId)
            );
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseV2Keys.documents(agentId) });
            toast.success("Tài liệu đã được xóa");
        },
        onError: (error: any) => {
            const message = error.response?.data?.detail || "Không thể xóa tài liệu";
            toast.error(message);
        },
    });
};

/**
 * Search documents in RAGFlow knowledge base
 */
export const useSearchDocuments = (agentId: string) => {
    return useMutation<RAGFlowSearchResult, Error, { query: string; k?: number }>({
        mutationFn: async ({ query, k = 5 }) => {
            const { data } = await apiClient.post(KNOWLEDGE_BASE_V2_ENDPOINTS.SEARCH(agentId), {
                query,
                k,
            });
            return data.data;
        },
        onError: (error: any) => {
            const message = error.response?.data?.detail || "Không thể tìm kiếm";
            toast.error(message);
        },
    });
};
