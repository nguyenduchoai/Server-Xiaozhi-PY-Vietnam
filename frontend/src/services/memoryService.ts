/**
 * Memory Service - API client cho quản lý conversation memories
 */
import apiClient from "@/config/axios-instance";

// ==================== Types ====================

export interface ConversationMemory {
    id: string;
    device_id: string;
    user_id?: string;
    agent_id?: string;
    key: string;
    value: string;
    memory_type: string;
    category?: string;
    confidence?: number;
    source?: string;
    expires_at?: string;
    created_at: string;
    updated_at: string;
}

export interface MemoryCreate {
    key: string;
    value: string;
    memory_type: string;
    category?: string;
    confidence?: number;
    source?: string;
}

export interface MemoryUpdate {
    value?: string;
    memory_type?: string;
    category?: string;
    confidence?: number;
}

export interface MemoryContext {
    user_facts: string[];
    preferences: Record<string, string>;
    habits: string[];
    recent_topics: string[];
    emotional_state?: string;
}

export interface EmotionLog {
    id: string;
    device_id: string;
    emotion: string;
    intensity: number;
    trigger?: string;
    context?: string;
    created_at: string;
}

export interface EmotionLogCreate {
    emotion: string;
    intensity: number;
    trigger?: string;
    context?: string;
}

export interface EmotionSummary {
    total_logs: number;
    dominant_emotion: string;
    emotion_distribution: Record<string, number>;
    average_intensity: number;
    mood_trend: string;
}

export interface SuccessResponse<T> {
    success: boolean;
    message?: string;
    data: T;
}

// ==================== Service ====================

const memoryService = {
    /**
     * Get all memories for a device
     */
    getDeviceMemories: async (
        deviceId: string,
        params?: { memory_type?: string; category?: string }
    ): Promise<SuccessResponse<ConversationMemory[]>> => {
        const response = await apiClient.get(`/memory/devices/${deviceId}`, { params });
        return response.data;
    },

    /**
     * Get a specific memory by key
     */
    getMemory: async (
        deviceId: string,
        key: string
    ): Promise<SuccessResponse<ConversationMemory>> => {
        const response = await apiClient.get(`/memory/devices/${deviceId}/${key}`);
        return response.data;
    },

    /**
     * Create or update a memory
     */
    createMemory: async (
        deviceId: string,
        data: MemoryCreate
    ): Promise<SuccessResponse<ConversationMemory>> => {
        const response = await apiClient.post(`/memory/devices/${deviceId}`, data);
        return response.data;
    },

    /**
     * Update an existing memory
     */
    updateMemory: async (
        deviceId: string,
        key: string,
        data: MemoryUpdate
    ): Promise<SuccessResponse<ConversationMemory>> => {
        const response = await apiClient.put(`/memory/devices/${deviceId}/${key}`, data);
        return response.data;
    },

    /**
     * Delete a memory
     */
    deleteMemory: async (deviceId: string, key: string): Promise<void> => {
        await apiClient.delete(`/memory/devices/${deviceId}/${key}`);
    },

    /**
     * Clear all memories for a device
     */
    clearMemories: async (
        deviceId: string,
        memoryType?: string
    ): Promise<void> => {
        await apiClient.delete(`/memory/devices/${deviceId}/clear`, {
            params: memoryType ? { memory_type: memoryType } : {},
        });
    },

    /**
     * Get memory context (aggregated for LLM)
     */
    getMemoryContext: async (
        deviceId: string
    ): Promise<SuccessResponse<MemoryContext>> => {
        const response = await apiClient.get(`/memory/devices/${deviceId}/context`);
        return response.data;
    },

    /**
     * Log a detected emotion
     */
    logEmotion: async (
        deviceId: string,
        data: EmotionLogCreate
    ): Promise<SuccessResponse<EmotionLog>> => {
        const response = await apiClient.post(`/memory/devices/${deviceId}/emotions`, data);
        return response.data;
    },

    /**
     * Get recent emotion logs
     */
    getRecentEmotions: async (
        deviceId: string,
        params?: { hours?: number; limit?: number }
    ): Promise<SuccessResponse<EmotionLog[]>> => {
        const response = await apiClient.get(`/memory/devices/${deviceId}/emotions`, { params });
        return response.data;
    },

    /**
     * Get emotion summary/statistics
     */
    getEmotionSummary: async (
        deviceId: string,
        hours: number = 24
    ): Promise<SuccessResponse<EmotionSummary>> => {
        const response = await apiClient.get(`/memory/devices/${deviceId}/emotions/summary`, {
            params: { hours },
        });
        return response.data;
    },

    /**
     * Learn from a user message (extract facts/preferences)
     */
    learnFromMessage: async (
        deviceId: string,
        message: string
    ): Promise<SuccessResponse<{ learned_count: number; items: ConversationMemory[] }>> => {
        const response = await apiClient.post(`/memory/devices/${deviceId}/learn`, null, {
            params: { message },
        });
        return response.data;
    },
};

export default memoryService;
