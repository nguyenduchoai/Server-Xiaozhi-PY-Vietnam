import { apiClient } from "@/config/axios-instance";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

export interface DashboardStats {
    total_devices: number;
    active_devices: number;
    total_agents: number;
    total_messages: number;
    messages_today: number;
    period_days: number;
    generated_at: string;
}

export interface DeviceStatus {
    id: string;
    name: string;
    mac_address: string;
    is_online: boolean;
    is_mqtt_connected?: boolean;
    last_seen: string | null;
    status: "online" | "available" | "offline";
}

export interface DeviceStatusResponse {
    devices: DeviceStatus[];
    total: number;
    online: number;
    available?: number;
    offline?: number;
}

export interface DailyUsage {
    date: string;
    messages: number;
    sessions: number;
}

export interface DailyUsageResponse {
    daily: DailyUsage[];
    period_days: number;
}

export const analyticsApi = {
    getDashboardStats: async (days: number = 7): Promise<DashboardStats> => {
        const response = await apiClient.get(API_ENDPOINTS.ANALYTICS.DASHBOARD, {
            params: { days },
        });
        return response.data;
    },

    getDailyUsage: async (days: number = 30): Promise<DailyUsageResponse> => {
        const response = await apiClient.get(API_ENDPOINTS.ANALYTICS.DAILY_USAGE, {
            params: { days },
        });
        return response.data;
    },

    getDeviceStatus: async (): Promise<DeviceStatusResponse> => {
        const response = await apiClient.get(API_ENDPOINTS.ANALYTICS.DEVICE_STATUS);
        return response.data;
    },
};
