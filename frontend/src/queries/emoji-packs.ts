/**
 * React Query hooks for Emoji Pack API
 */
import {
    useQuery,
    useMutation,
    useQueryClient,
} from "@tanstack/react-query";
import apiClient from "@config/axios-instance";


// Types
export interface EmojiPack {
    id: string;
    name: string;
    description?: string;
    target_size: number;
    base_pack: string;
    is_public: boolean;
    is_featured: boolean;
    approval_status: string;
    download_count: number;
    emotions: Record<string, EmotionAssetInfo>;
    created_at: string;
    updated_at?: string;
    author?: {
        id: string;
        name: string;
    };
}

export interface EmotionAssetInfo {
    url: string;
    file_type: string;
    is_custom: boolean;
    has_animation?: boolean;
    frame_count?: number;
    file_size?: number;
}

export interface EmojiPackListItem {
    id: string;
    name: string;
    description?: string;
    target_size: number;
    base_pack: string;
    emotion_count: number;
    is_public: boolean;
    is_featured: boolean;
    download_count: number;
    preview_url: string;
    created_at: string;
    author?: {
        id: string;
        name: string;
    };
}

export interface EmojiPackListResponse {
    success: boolean;
    data: EmojiPackListItem[];
    total: number;
    page: number;
    page_size: number;
}

export interface CreateEmojiPackPayload {
    name: string;
    description?: string;
    target_size?: number;
    base_pack?: string;
}

export interface UpdateEmojiPackPayload {
    name?: string;
    description?: string;
    target_size?: number;
    base_pack?: string;
}

// Query keys
export const emojiPackKeys = {
    all: ["emoji-packs"] as const,
    list: (filters: Record<string, unknown>) => [...emojiPackKeys.all, "list", filters] as const,
    community: (filters: Record<string, unknown>) => [...emojiPackKeys.all, "community", filters] as const,
    detail: (id: string) => [...emojiPackKeys.all, "detail", id] as const,
};

// API functions
const emojiPackApi = {
    list: async (params: {
        filter?: string;
        search?: string;
        page?: number;
        page_size?: number;
    }): Promise<EmojiPackListResponse> => {
        const searchParams = new URLSearchParams();
        if (params.filter) searchParams.append("filter", params.filter);
        if (params.search) searchParams.append("search", params.search);
        if (params.page) searchParams.append("page", String(params.page));
        if (params.page_size) searchParams.append("page_size", String(params.page_size));

        const response = await apiClient.get(`/emoji-packs?${searchParams.toString()}`);
        return response.data;
    },

    community: async (params: {
        search?: string;
        featured_only?: boolean;
        page?: number;
        page_size?: number;
    }): Promise<EmojiPackListResponse> => {
        const searchParams = new URLSearchParams();
        if (params.search) searchParams.append("search", params.search);
        if (params.featured_only) searchParams.append("featured_only", "true");
        if (params.page) searchParams.append("page", String(params.page));
        if (params.page_size) searchParams.append("page_size", String(params.page_size));

        const response = await apiClient.get(`/emoji-packs/community?${searchParams.toString()}`);
        return response.data;
    },

    get: async (id: string): Promise<EmojiPack> => {
        const response = await apiClient.get(`/emoji-packs/${id}`);
        return response.data;
    },

    create: async (payload: CreateEmojiPackPayload): Promise<EmojiPack> => {
        const response = await apiClient.post("/emoji-packs", payload);
        return response.data;
    },

    update: async (id: string, payload: UpdateEmojiPackPayload): Promise<EmojiPack> => {
        const response = await apiClient.patch(`/emoji-packs/${id}`, payload);
        return response.data;
    },

    delete: async (id: string): Promise<void> => {
        await apiClient.delete(`/emoji-packs/${id}`);
    },

    uploadEmotion: async (
        packId: string,
        emotion: string,
        file: File
    ): Promise<EmotionAssetInfo & { emotion: string }> => {
        const formData = new FormData();
        formData.append("file", file);

        const response = await apiClient.post(
            `/emoji-packs/${packId}/emotions/${emotion}`,
            formData,
            {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            }
        );
        return response.data;
    },

    deleteEmotion: async (packId: string, emotion: string): Promise<void> => {
        await apiClient.delete(`/emoji-packs/${packId}/emotions/${emotion}`);
    },

    share: async (
        packId: string,
        shareType: "public" | "private"
    ): Promise<{ success: boolean; approval_status: string; message: string }> => {
        const response = await apiClient.post(`/emoji-packs/${packId}/share`, {
            share_type: shareType,
        });
        return response.data;
    },

    clone: async (packId: string): Promise<EmojiPack> => {
        const response = await apiClient.post(`/emoji-packs/${packId}/clone`);
        return response.data;
    },
};

// Hooks
export function useEmojiPackList(params: {
    filter?: string;
    search?: string;
    page?: number;
    page_size?: number;
}) {
    return useQuery({
        queryKey: emojiPackKeys.list(params),
        queryFn: () => emojiPackApi.list(params),
    });
}

export function useCommunityEmojiPacks(params: {
    search?: string;
    featured_only?: boolean;
    page?: number;
    page_size?: number;
}) {
    return useQuery({
        queryKey: emojiPackKeys.community(params),
        queryFn: () => emojiPackApi.community(params),
    });
}

export function useEmojiPackDetail(id: string) {
    return useQuery({
        queryKey: emojiPackKeys.detail(id),
        queryFn: () => emojiPackApi.get(id),
        enabled: Boolean(id),
    });
}

export function useCreateEmojiPack() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: emojiPackApi.create,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.all });
        },
    });
}

export function useUpdateEmojiPack() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, payload }: { id: string; payload: UpdateEmojiPackPayload }) =>
            emojiPackApi.update(id, payload),
        onSuccess: (_, { id }) => {
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.detail(id) });
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.all });
        },
    });
}

export function useDeleteEmojiPack() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: emojiPackApi.delete,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.all });
        },
    });
}

export function useUploadEmotion() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({
            packId,
            emotion,
            file,
        }: {
            packId: string;
            emotion: string;
            file: File;
        }) => emojiPackApi.uploadEmotion(packId, emotion, file),
        onSuccess: (_, { packId }) => {
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.detail(packId) });
        },
    });
}

export function useDeleteEmotion() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ packId, emotion }: { packId: string; emotion: string }) =>
            emojiPackApi.deleteEmotion(packId, emotion),
        onSuccess: (_, { packId }) => {
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.detail(packId) });
        },
    });
}

export function useShareEmojiPack() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({
            packId,
            shareType,
        }: {
            packId: string;
            shareType: "public" | "private";
        }) => emojiPackApi.share(packId, shareType),
        onSuccess: (_, { packId }) => {
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.detail(packId) });
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.all });
        },
    });
}

export function useCloneEmojiPack() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: emojiPackApi.clone,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: emojiPackKeys.all });
        },
    });
}
