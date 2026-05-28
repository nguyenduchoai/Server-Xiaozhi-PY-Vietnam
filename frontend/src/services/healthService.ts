/**
 * Health Service - System Health API Client
 * Provides access to health check endpoints for the System Health Dashboard
 */

import apiClient from "@/config/axios-instance";

// Response types
export interface ComponentHealth {
    status: "healthy" | "unhealthy" | "degraded";
    latency_ms: number | null;
    details: string | null;
    last_check: string | null;
}

export interface DetailedHealthCheck {
    status: "healthy" | "unhealthy" | "degraded";
    environment: string;
    version: string;
    uptime_seconds: number;
    timestamp: string;
    components: Record<string, ComponentHealth>;
}

export interface MonitoringLinks {
    grafana_url: string | null;
    prometheus_url: string | null;
    grafana_status: "available" | "unavailable";
    prometheus_status: "available" | "unavailable";
}

// Health API Endpoints
const HEALTH_ENDPOINTS = {
    BASIC: "/health",
    READY: "/ready",
    DETAILED: "/health/detailed",
    MONITORING_LINKS: "/health/monitoring-links",
};

/**
 * Get basic health status (no auth required)
 */
export const getBasicHealth = async () => {
    const response = await apiClient.get(HEALTH_ENDPOINTS.BASIC);
    return response.data;
};

/**
 * Get readiness status (no auth required)
 */
export const getReadyStatus = async () => {
    const response = await apiClient.get(HEALTH_ENDPOINTS.READY);
    return response.data;
};

/**
 * Get detailed health status of all components (admin only)
 */
export const getDetailedHealth = async (): Promise<DetailedHealthCheck> => {
    const response = await apiClient.get<DetailedHealthCheck>(
        HEALTH_ENDPOINTS.DETAILED
    );
    return response.data;
};

/**
 * Get monitoring dashboard links (admin only)
 */
export const getMonitoringLinks = async (): Promise<MonitoringLinks> => {
    const response = await apiClient.get<MonitoringLinks>(
        HEALTH_ENDPOINTS.MONITORING_LINKS
    );
    return response.data;
};

/**
 * Format uptime seconds to human readable string
 */
export const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

    return parts.join(" ");
};

/**
 * Get status color for Semi Design
 */
export const getStatusColor = (
    status: string
): "success" | "warning" | "danger" | "default" => {
    switch (status) {
        case "healthy":
            return "success";
        case "degraded":
            return "warning";
        case "unhealthy":
            return "danger";
        default:
            return "default";
    }
};

/**
 * Get status icon name
 */
export const getStatusIcon = (status: string): string => {
    switch (status) {
        case "healthy":
            return "check_circle";
        case "degraded":
            return "warning";
        case "unhealthy":
            return "error";
        default:
            return "help";
    }
};

export default {
    getBasicHealth,
    getReadyStatus,
    getDetailedHealth,
    getMonitoringLinks,
    formatUptime,
    getStatusColor,
    getStatusIcon,
};
