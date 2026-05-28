import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/config/axios-instance";

// Types
export interface ThemeColors {
    primary: string;
    secondary: string;
    background: string;
    text: string;
}

export interface ThemeData {
    colors: ThemeColors;
    widgets?: {
        clock?: { enabled: boolean; format?: string };
        weather?: { enabled: boolean };
        calendar?: { enabled: boolean };
    };
}

export interface Theme {
    id: string;
    name: string;
    description: string | null;
    preview_url: string | null;
    screen_type: string;
    category: string;
    is_system: boolean;
    download_count: number;
    theme_data?: ThemeData;
    created_at: string;
}

export interface ThemeListResponse {
    themes: Theme[];
    total: number;
    page: number;
    limit: number;
}

export interface ThemeCategory {
    id: string;
    name: string;
    icon: string;
}

export interface ScreenType {
    id: string;
    name: string;
    description: string;
}

export interface WidgetConfig {
    clock: boolean;
    weather: boolean;
    calendar: boolean;
    lunar: boolean;
}

export interface DeviceThemeInfo {
    device_id: string;
    theme: {
        id: string;
        name: string;
        preview_url: string | null;
    } | null;
    widgets: WidgetConfig;
    installed_at: string | null;
}

// Query keys
export const themeKeys = {
    all: ["themes"] as const,
    lists: () => [...themeKeys.all, "list"] as const,
    list: (filters: Record<string, unknown>) => [...themeKeys.lists(), filters] as const,
    categories: () => [...themeKeys.all, "categories"] as const,
    screenTypes: () => [...themeKeys.all, "screen-types"] as const,
    detail: (id: string) => [...themeKeys.all, "detail", id] as const,
    deviceTheme: (deviceId: string) => [...themeKeys.all, "device", deviceId] as const,
};

// Fetch themes
export function useThemes(filters?: {
    screen_type?: string;
    category?: string;
    search?: string;
    page?: number;
    limit?: number;
}) {
    return useQuery({
        queryKey: themeKeys.list(filters || {}),
        queryFn: async (): Promise<ThemeListResponse> => {
            const params = new URLSearchParams();
            if (filters?.screen_type) params.append("screen_type", filters.screen_type);
            if (filters?.category) params.append("category", filters.category);
            if (filters?.search) params.append("search", filters.search);
            if (filters?.page) params.append("page", String(filters.page));
            if (filters?.limit) params.append("limit", String(filters.limit));

            const response = await apiClient.get(`/themes?${params.toString()}`);
            return response.data;
        },
    });
}

// Fetch categories
export function useThemeCategories() {
    return useQuery({
        queryKey: themeKeys.categories(),
        queryFn: async () => {
            const response = await apiClient.get("/themes/categories");
            return response.data.categories as ThemeCategory[];
        },
    });
}

// Fetch screen types
export function useScreenTypes() {
    return useQuery({
        queryKey: themeKeys.screenTypes(),
        queryFn: async () => {
            const response = await apiClient.get("/themes/screen-types");
            return response.data.screen_types as ScreenType[];
        },
    });
}

// Fetch theme detail
export function useTheme(themeId: string) {
    return useQuery({
        queryKey: themeKeys.detail(themeId),
        queryFn: async (): Promise<Theme> => {
            const response = await apiClient.get(`/themes/${themeId}`);
            return response.data;
        },
        enabled: !!themeId,
    });
}

// Fetch device's current theme
export function useDeviceTheme(deviceId: string) {
    return useQuery({
        queryKey: themeKeys.deviceTheme(deviceId),
        queryFn: async (): Promise<DeviceThemeInfo> => {
            const response = await apiClient.get(`/themes/devices/${deviceId}/current`);
            return response.data;
        },
        enabled: !!deviceId,
    });
}

// Apply theme to device
export function useApplyTheme() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            deviceId,
            themeId,
            widgets,
        }: {
            deviceId: string;
            themeId: string;
            widgets?: WidgetConfig;
        }) => {
            const response = await apiClient.post(`/themes/devices/${deviceId}/apply`, {
                theme_id: themeId,
                widgets,
            });
            return response.data;
        },
        onSuccess: (_, { deviceId }) => {
            queryClient.invalidateQueries({ queryKey: themeKeys.deviceTheme(deviceId) });
            queryClient.invalidateQueries({ queryKey: themeKeys.lists() });
        },
    });
}

// Update device widgets
export function useUpdateWidgets() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            deviceId,
            widgets,
        }: {
            deviceId: string;
            widgets: WidgetConfig;
        }) => {
            const response = await apiClient.put(`/themes/devices/${deviceId}/widgets`, widgets);
            return response.data;
        },
        onSuccess: (_, { deviceId }) => {
            queryClient.invalidateQueries({ queryKey: themeKeys.deviceTheme(deviceId) });
        },
    });
}

// Create custom theme
export function useCreateTheme() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: {
            name: string;
            description?: string;
            screen_type?: string;
            category?: string;
            theme_data?: Record<string, unknown>;
        }) => {
            const response = await apiClient.post("/themes", data);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: themeKeys.lists() });
        },
    });
}

// Delete theme
export function useDeleteTheme() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (themeId: string) => {
            const response = await apiClient.delete(`/themes/${themeId}`);
            return response.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: themeKeys.lists() });
        },
    });
}
