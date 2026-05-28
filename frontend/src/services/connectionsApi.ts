/**
 * Frontend API service for User Connections (Integrations).
 * Centralized channel configuration — configure once, use everywhere.
 */

import { apiClient } from "@/config/axios-instance";

// ============ Types ============

export interface UserConnection {
    id: string;
    user_id: string;
    type: ConnectionType;
    name: string;
    config: Record<string, unknown>;
    enabled: boolean;
    status: string;
    status_info?: Record<string, unknown> | null;
    created_at: string;
    updated_at: string;
}

export type ConnectionType = "telegram" | "zalo_oa" | "smtp" | "imap";

export interface ConnectionCreate {
    type: ConnectionType;
    name: string;
    config: Record<string, unknown>;
    enabled?: boolean;
}

export interface ConnectionUpdate {
    name?: string;
    config?: Record<string, unknown>;
    enabled?: boolean;
}

export interface TestResult {
    success: boolean;
    error?: string;
    [key: string]: unknown;
}

// ============ API ============

const connectionsApi = {
    /** List all connections for current user */
    list: async (type?: ConnectionType): Promise<{ connections: UserConnection[]; total: number }> => {
        const params: Record<string, string> = {};
        if (type) params.type = type;
        const response = await apiClient.get("/connections", { params });
        return response.data;
    },

    /** Get a specific connection */
    get: async (id: string): Promise<UserConnection> => {
        const response = await apiClient.get(`/connections/${id}`);
        return response.data;
    },

    /** Create a new connection */
    create: async (data: ConnectionCreate): Promise<UserConnection> => {
        const response = await apiClient.post("/connections", data);
        return response.data;
    },

    /** Update a connection */
    update: async (id: string, data: ConnectionUpdate): Promise<UserConnection> => {
        const response = await apiClient.put(`/connections/${id}`, data);
        return response.data;
    },

    /** Delete a connection */
    delete: async (id: string): Promise<{ success: boolean }> => {
        const response = await apiClient.delete(`/connections/${id}`);
        return response.data;
    },

    /** Test a connection */
    test: async (id: string): Promise<TestResult> => {
        const response = await apiClient.post(`/connections/${id}/test`);
        return response.data;
    },

    /** Send a real test message */
    sendTest: async (id: string, recipient: string, message?: string): Promise<TestResult> => {
        const response = await apiClient.post(`/connections/${id}/send-test`, {
            recipient,
            message: message || "🔔 Test từ Xiaozhi AI IOT",
        });
        return response.data;
    },

};

export default connectionsApi;
