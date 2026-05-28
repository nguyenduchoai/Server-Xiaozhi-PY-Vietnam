import { apiClient } from "@/config/axios-instance";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

export interface MqttDevicesResponse {
    mqtt_connected_devices: string[];
    count: number;
    tracking_active: boolean;
}

export interface AllDevicesResponse {
    devices: Record<string, { websocket: boolean; mqtt: boolean }>;
    websocket_count: number;
    mqtt_count: number;
    total_unique: number;
}

export const notificationApi = {
    send: async (deviceId: string, message: string, type: "info" | "warning" | "alert" | "reminder" = "info", speak: boolean = true) => {
        const response = await apiClient.post(API_ENDPOINTS.NOTIFICATIONS.SEND(deviceId), {
            message,
            notification_type: type,
            speak,
        });
        return response.data;
    },

    broadcast: async (message: string, type: "info" | "warning" | "alert" | "reminder" = "info", speak: boolean = true) => {
        const response = await apiClient.post(API_ENDPOINTS.NOTIFICATIONS.BROADCAST, {
            message,
            notification_type: type,
            speak,
        });
        return response.data;
    },

    speak: async (deviceId: string, message: string) => {
        const response = await apiClient.post(API_ENDPOINTS.NOTIFICATIONS.SPEAK(deviceId), null, {
            params: { message }
        });
        return response.data;
    },

    getMqttDevices: async (): Promise<MqttDevicesResponse> => {
        const response = await apiClient.get(API_ENDPOINTS.NOTIFICATIONS.MQTT_DEVICES);
        return response.data;
    },

    getAllAvailableDevices: async (): Promise<AllDevicesResponse> => {
        const response = await apiClient.get(API_ENDPOINTS.NOTIFICATIONS.ALL_DEVICES);
        return response.data;
    },
};
