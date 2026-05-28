import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/config/axios-instance";

// Types
export interface ServerConfig {
    id: string;
    name: string;
    description?: string;
    websocket_url: string;
    api_url: string;
    mqtt_host?: string;
    mqtt_port: number;
    mqtt_username?: string;
    is_default: boolean;
    is_active: boolean;
    region?: string;
    created_at?: string;
}

export interface DeviceServerAssignment {
    device_id: string;
    server: ServerConfig | null;
    is_default: boolean;
}

// Query keys
export const serverKeys = {
    all: ["servers"] as const,
    list: () => [...serverKeys.all, "list"] as const,
    detail: (id: string) => [...serverKeys.all, "detail", id] as const,
    deviceServer: (deviceId: string) => [...serverKeys.all, "device", deviceId] as const,
};

// Hooks

/**
 * Get list of available servers
 */
export function useServers(region?: string) {
    return useQuery({
        queryKey: serverKeys.list(),
        queryFn: async () => {
            const params = new URLSearchParams();
            if (region) params.append("region", region);

            const response = await apiClient.get<ServerConfig[]>(
                `/servers${params.toString() ? `?${params.toString()}` : ""}`
            );
            return response.data;
        },
    });
}

/**
 * Get server details
 */
export function useServerDetail(serverId: string | undefined) {
    return useQuery({
        queryKey: serverKeys.detail(serverId || ""),
        queryFn: async () => {
            if (!serverId) throw new Error("Server ID required");
            const response = await apiClient.get<ServerConfig>(`/servers/${serverId}`);
            return response.data;
        },
        enabled: !!serverId,
    });
}

/**
 * Get device's server assignment
 */
export function useDeviceServer(deviceId: string | undefined) {
    return useQuery({
        queryKey: serverKeys.deviceServer(deviceId || ""),
        queryFn: async () => {
            if (!deviceId) throw new Error("Device ID required");
            const response = await apiClient.get<DeviceServerAssignment>(
                `/servers/devices/${deviceId}/server`
            );
            return response.data;
        },
        enabled: !!deviceId,
    });
}

/**
 * Create a new server config (Admin only)
 */
export function useCreateServer() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: Omit<ServerConfig, "id" | "created_at" | "is_default" | "is_active">) => {
            const response = await apiClient.post<ServerConfig>("/servers", data);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: serverKeys.list() });
        },
    });
}

/**
 * Update server config (Admin only)
 */
export function useUpdateServer() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            serverId,
            data,
        }: {
            serverId: string;
            data: Partial<ServerConfig>;
        }) => {
            const response = await apiClient.put<ServerConfig>(`/servers/${serverId}`, data);
            return response.data;
        },
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: serverKeys.list() });
            queryClient.invalidateQueries({ queryKey: serverKeys.detail(variables.serverId) });
        },
    });
}

/**
 * Delete server config (Admin only)
 */
export function useDeleteServer() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (serverId: string) => {
            const response = await apiClient.delete(`/servers/${serverId}`);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: serverKeys.list() });
        },
    });
}

/**
 * Assign device to server
 */
export function useAssignDeviceServer() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            deviceId,
            serverId,
        }: {
            deviceId: string;
            serverId: string;
        }) => {
            const response = await apiClient.put(
                `/servers/devices/${deviceId}/server`,
                { server_id: serverId }
            );
            return response.data;
        },
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({
                queryKey: serverKeys.deviceServer(variables.deviceId),
            });
        },
    });
}

/**
 * Reset device to default server
 */
export function useResetDeviceServer() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (deviceId: string) => {
            const response = await apiClient.post(
                `/servers/devices/${deviceId}/reset-server`
            );
            return response.data;
        },
        onSuccess: (_, deviceId) => {
            queryClient.invalidateQueries({
                queryKey: serverKeys.deviceServer(deviceId),
            });
        },
    });
}
