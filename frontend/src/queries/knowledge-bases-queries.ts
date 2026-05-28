/**
 * React Query hooks for Knowledge Base API
 * 
 * Manages independent knowledge bases (CRUD operations)
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/config/axios-instance';

// ============================================================================
// Types
// ============================================================================

export interface KnowledgeBase {
    id: string;
    name: string;
    description: string | null;
    ragflow_dataset_id: string | null;
    embedding_model: string;
    entry_count: number;
    agent_count: number;
    created_at: string;
    updated_at: string;
}

export interface KnowledgeBaseListResponse {
    items: KnowledgeBase[];
    total: number;
    page: number;
    page_size: number;
}

export interface KnowledgeBaseCreate {
    name: string;
    description?: string;
    embedding_model?: string;
}

export interface KnowledgeBaseUpdate {
    name?: string;
    description?: string;
    embedding_model?: string;
}

export interface KnowledgeEntry {
    id: string;
    content: string;
    doc_type: string;
    source: string;
    metadata_json: string | null;
    created_at: string;
    updated_at: string;
}

export interface KnowledgeEntryListResponse {
    items: KnowledgeEntry[];
    total: number;
    page: number;
    page_size: number;
}

export interface KnowledgeEntryCreate {
    content: string;
    doc_type?: string;
    source?: string;
    metadata?: Record<string, unknown>;
}

// ============================================================================
// Query Keys
// ============================================================================

export const knowledgeBaseKeys = {
    all: ['knowledge-bases'] as const,
    lists: () => [...knowledgeBaseKeys.all, 'list'] as const,
    list: (params: { page?: number; search?: string }) => [...knowledgeBaseKeys.lists(), params] as const,
    details: () => [...knowledgeBaseKeys.all, 'detail'] as const,
    detail: (id: string) => [...knowledgeBaseKeys.details(), id] as const,
    entries: (kbId: string) => [...knowledgeBaseKeys.all, kbId, 'entries'] as const,
    entriesList: (kbId: string, params: { page?: number }) => [...knowledgeBaseKeys.entries(kbId), params] as const,
};

// ============================================================================
// Knowledge Base Queries
// ============================================================================

export function useKnowledgeBases(params: { page?: number; search?: string } = {}) {
    return useQuery({
        queryKey: knowledgeBaseKeys.list(params),
        queryFn: async () => {
            const searchParams = new URLSearchParams();
            if (params.page) searchParams.set('page', params.page.toString());
            if (params.search) searchParams.set('search', params.search);

            const { data } = await apiClient.get<KnowledgeBaseListResponse>(
                `/knowledge-bases?${searchParams.toString()}`
            );
            return data;
        },
    });
}

export function useKnowledgeBase(id: string) {
    return useQuery({
        queryKey: knowledgeBaseKeys.detail(id),
        queryFn: async () => {
            const { data } = await apiClient.get<KnowledgeBase>(`/knowledge-bases/${id}`);
            return data;
        },
        enabled: !!id,
    });
}

// ============================================================================
// Knowledge Base Mutations
// ============================================================================

export function useCreateKnowledgeBase() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (payload: KnowledgeBaseCreate) => {
            const { data } = await apiClient.post<KnowledgeBase>('/knowledge-bases', payload);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.lists() });
        },
    });
}

export function useUpdateKnowledgeBase() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ id, ...payload }: KnowledgeBaseUpdate & { id: string }) => {
            const { data } = await apiClient.put<KnowledgeBase>(`/knowledge-bases/${id}`, payload);
            return data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.lists() });
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.detail(data.id) });
        },
    });
}

export function useDeleteKnowledgeBase() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (id: string) => {
            await apiClient.delete(`/knowledge-bases/${id}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.lists() });
        },
    });
}

// ============================================================================
// Knowledge Entry Queries
// ============================================================================

export function useKnowledgeEntries(kbId: string, params: { page?: number } = {}) {
    return useQuery({
        queryKey: knowledgeBaseKeys.entriesList(kbId, params),
        queryFn: async () => {
            const searchParams = new URLSearchParams();
            if (params.page) searchParams.set('page', params.page.toString());

            const { data } = await apiClient.get<KnowledgeEntryListResponse>(
                `/knowledge-bases/${kbId}/entries?${searchParams.toString()}`
            );
            return data;
        },
        enabled: !!kbId,
    });
}

// ============================================================================
// Knowledge Entry Mutations
// ============================================================================

export function useCreateKnowledgeEntry(kbId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (payload: KnowledgeEntryCreate) => {
            const { data } = await apiClient.post<KnowledgeEntry>(
                `/knowledge-bases/${kbId}/entries`,
                payload
            );
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.entries(kbId) });
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.detail(kbId) });
        },
    });
}

export function useUploadKnowledgeEntry(kbId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append('file', file);

            const { data } = await apiClient.post<KnowledgeEntry>(
                `/knowledge-bases/${kbId}/entries/upload`,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                }
            );
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.entries(kbId) });
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.detail(kbId) });
        },
    });
}

export function useDeleteKnowledgeEntry(kbId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (entryId: string) => {
            await apiClient.delete(`/knowledge-bases/${kbId}/entries/${entryId}`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.entries(kbId) });
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.detail(kbId) });
        },
    });
}

// ============================================================================
// Agent-KB Linking
// ============================================================================

export interface AgentKnowledgeBaseLink {
    id: string;
    name: string;
}

export function useAgentKnowledgeBases(agentId: string) {
    return useQuery({
        queryKey: ['agents', agentId, 'knowledge-bases'] as const,
        queryFn: async () => {
            const { data } = await apiClient.get<{ knowledge_bases: AgentKnowledgeBaseLink[] }>(
                `/agents/${agentId}/knowledge-bases`
            );
            return data.knowledge_bases;
        },
        enabled: !!agentId,
    });
}

export function useUpdateAgentKnowledgeBases(agentId: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (kbIds: string[]) => {
            const { data } = await apiClient.put<{ knowledge_bases: AgentKnowledgeBaseLink[] }>(
                `/agents/${agentId}/knowledge-bases`,
                { knowledge_base_ids: kbIds }
            );
            return data.knowledge_bases;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['agents', agentId, 'knowledge-bases'] });
            queryClient.invalidateQueries({ queryKey: knowledgeBaseKeys.lists() });
        },
    });
}
