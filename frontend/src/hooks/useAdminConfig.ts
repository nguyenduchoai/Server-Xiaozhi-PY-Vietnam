import { useQuery } from "@tanstack/react-query";
import { apiClient as request } from "@/config/axios-instance"; // Use centralized axios instance

export interface SystemConfig {
    mqtt?: {
        url?: string;
        broker?: string;
        port?: number;
        username?: string;
        password?: string;
        topic_prefix?: string;
    };
    [key: string]: any;
}

export function useAdminConfig(includeSensitive = false) {
    return useQuery({
        queryKey: ["admin", "config", includeSensitive],
        queryFn: async () => {
            const { data } = await request.get<{ config: SystemConfig }>(
                "/admin/config",
                {
                    params: { include_sensitive: includeSensitive },
                }
            );
            return data.config;
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}
