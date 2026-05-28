/**
 * Notification Channels API - Manage Telegram, Zalo OA, Escalation, Daily Report
 * Per-agent multi-channel notification configuration
 */
import { apiClient } from "@/config/axios-instance";

// ============ Types ============

export interface TelegramConfig {
    enabled: boolean;
    bot_token: string;
    chat_ids: string[];
}

/** Zalo OA Bot — Official Account with API token */
export interface ZaloOAConfig {
    enabled: boolean;
    oa_access_token: string;
    user_ids: string[];
}

export interface EscalationLevel {
    channels: string[];
}

export interface AlertEscalationConfig {
    enabled: boolean;
    levels: {
        info: EscalationLevel;
        warning: EscalationLevel;
        critical: EscalationLevel;
        sos: EscalationLevel;
    };
}

export interface DailyReportConfig {
    enabled: boolean;
    time: string;
    timezone: string;
    channels: string[];
}

/** Per-agent channel with recipient selection */
export interface AgentChannel {
    connection_id: string;
    recipients: string[];
    enabled: boolean;
}

export interface NotificationChannelsConfig {
    telegram?: TelegramConfig;
    zalo_oa?: ZaloOAConfig;
    alert_escalation?: AlertEscalationConfig;
    daily_report?: DailyReportConfig;
    connections?: string[];  // Legacy: simple IDs
    channels?: AgentChannel[];  // New: connections + recipients
}

export interface TestNotificationRequest {
    message: string;
    level: string;
    channels?: string[];
}

export interface TestResult {
    [channel: string]: {
        success: boolean;
        error?: string;
        bot_name?: string;
        displayName?: string;
        ownId?: string;
        delivery?: Record<string, boolean>;
    };
}

// ============ API Functions ============

export const notificationChannelsApi = {
    /** Get notification channels config for an agent */
    getConfig: async (agentId: string): Promise<NotificationChannelsConfig> => {
        const response = await apiClient.get(`/agents/${agentId}/notification-channels`);
        return response.data?.data || {};
    },

    /** Update full notification channels config */
    updateConfig: async (agentId: string, config: NotificationChannelsConfig): Promise<NotificationChannelsConfig> => {
        const response = await apiClient.put(`/agents/${agentId}/notification-channels`, config);
        return response.data?.data || {};
    },

    /** Update a single channel config */
    updateChannel: async (agentId: string, channel: string, config: Record<string, unknown>): Promise<NotificationChannelsConfig> => {
        const response = await apiClient.patch(`/agents/${agentId}/notification-channels/${channel}`, config);
        return response.data?.data || {};
    },

    /** Disable (remove) a channel */
    disableChannel: async (agentId: string, channel: string): Promise<void> => {
        await apiClient.delete(`/agents/${agentId}/notification-channels/${channel}`);
    },

    /** Test notification delivery */
    testNotification: async (agentId: string, data: TestNotificationRequest): Promise<TestResult> => {
        // Explicitly attach token to prevent 401s if interceptor fails on this specific endpoint
        const token = localStorage.getItem("access_token");
        const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
        
        const response = await apiClient.post(`/agents/${agentId}/notification-channels/test`, data, { headers });
        return response.data?.data || {};
    },
};

export default notificationChannelsApi;
