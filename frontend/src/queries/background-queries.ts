import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/config/axios-instance";

// Types
export interface Background {
    id: string;
    device_id: string;
    background_type: string;
    file_url: string;
    file_size: number;
    width: number;
    height: number;
    uploaded_at: string;
}

export interface BackgroundListResponse {
    backgrounds: Background[];
    total: number;
}

export interface UploadBackgroundResponse {
    success: boolean;
    message: string;
    background: Background;
}

// Query keys
export const backgroundKeys = {
    all: ["backgrounds"] as const,
    device: (deviceId: string) => [...backgroundKeys.all, "device", deviceId] as const,
};

// Hooks

/**
 * Get list of backgrounds for a device
 */
export function useDeviceBackgrounds(deviceId: string | undefined) {
    return useQuery({
        queryKey: backgroundKeys.device(deviceId || ""),
        queryFn: async () => {
            if (!deviceId) throw new Error("Device ID required");
            const response = await apiClient.get<BackgroundListResponse>(
                `/devices/${deviceId}/backgrounds`
            );
            return response.data;
        },
        enabled: !!deviceId,
    });
}

/**
 * Upload a background image
 */
export function useUploadBackground() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            deviceId,
            file,
            backgroundType = "idle",
            screenType = "240x240",
        }: {
            deviceId: string;
            file: File;
            backgroundType?: string;
            screenType?: string;
        }) => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("background_type", backgroundType);
            formData.append("screen_type", screenType);

            const response = await apiClient.post<UploadBackgroundResponse>(
                `/devices/${deviceId}/backgrounds/upload`,
                formData,
                {
                    headers: { "Content-Type": "multipart/form-data" },
                }
            );
            return response.data;
        },
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({
                queryKey: backgroundKeys.device(variables.deviceId),
            });
        },
    });
}

/**
 * Delete a background
 */
export function useDeleteBackground() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            deviceId,
            backgroundId,
        }: {
            deviceId: string;
            backgroundId: string;
        }) => {
            const response = await apiClient.delete(
                `/devices/${deviceId}/backgrounds/${backgroundId}`
            );
            return response.data;
        },
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({
                queryKey: backgroundKeys.device(variables.deviceId),
            });
        },
    });
}

/**
 * Apply a background to device
 */
export function useApplyBackground() {
    return useMutation({
        mutationFn: async ({
            deviceId,
            backgroundType,
            fileUrl,
        }: {
            deviceId: string;
            backgroundType: string;
            fileUrl: string;
        }) => {
            const formData = new FormData();
            formData.append("background_type", backgroundType);
            formData.append("file_url", fileUrl);

            const response = await apiClient.post(
                `/devices/${deviceId}/backgrounds/apply`,
                formData,
                {
                    headers: { "Content-Type": "multipart/form-data" },
                }
            );
            return response.data;
        },
    });
}
