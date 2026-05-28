/**
 * Xiaozhi CE - Admin & Subscription API Service
 * CE version: subscription features are stubs, admin features are functional
 */
import { apiClient } from "@/config/axios-instance";

export interface SubscriptionPlan {
  id: number;
  name: string;
  display_name: string;
  description: string | null;
  price_monthly: number;
  price_yearly: number | null;
  max_agents: number;
  max_devices: number;
  max_monthly_tokens: number;
  max_knowledge_base_size_mb: number;
  max_tts_minutes_monthly: number;
  max_mcps: number;
  max_templates: number;
  max_tools: number;
  enable_api_access: boolean;
  enable_webhook: boolean;
  enable_custom_branding: boolean;
  enable_priority_support: boolean;
  allowed_provider_types: string[] | null;
  allow_custom_providers: boolean;
  allowed_provider_categories: string[] | null;
  sort_order: number;
}

export interface UserSubscription {
  id: string;
  user_id: string;
  plan_id: number;
  status: "active" | "pending" | "expired" | "cancelled";
  billing_cycle: "monthly" | "yearly" | "lifetime";
  expires_at: string | null;
  monthly_tokens_used: number;
  plan: SubscriptionPlan;
}

export interface SubscriptionUsage {
  agents_count: number;
  agents_limit: number;
  devices_count: number;
  devices_limit: number;
  tokens_used: number;
  tokens_limit: number;
  monthly_tokens_used: number;
  monthly_tokens_limit: number;
  monthly_tts_minutes_used: number;
  monthly_tts_minutes_limit: number;
  usage_percentage: number;
  usage_percent: {
    agents: number;
    devices: number;
    tokens: number;
    tts_minutes: number;
  };
}

// CE: Subscription API (limited - no payment features)
export const subscriptionApi = {
  getPlans: async (): Promise<SubscriptionPlan[]> => {
    const response = await apiClient.get("/subscription/plans");
    return response.data;
  },

  getMySubscription: async (): Promise<UserSubscription> => {
    const response = await apiClient.get("/subscription/me");
    return response.data;
  },

  getMyUsage: async (): Promise<SubscriptionUsage> => {
    const response = await apiClient.get("/subscription/me/usage");
    return response.data;
  },
};

// Admin API (fully functional)
export const adminApi = {
  // Get all users
  getUsers: async (params?: {
    search?: string;
    is_superuser?: boolean;
    page?: number;
    page_size?: number;
    include_deleted?: boolean;
  }) => {
    const response = await apiClient.get("/admin/users", { params });
    return response.data;
  },

  // Manually assign subscription
  assignSubscription: async (userId: string, data: {
    plan_id: number;
    billing_cycle?: string;
    duration_days?: number;
  }) => {
    const response = await apiClient.post(`/admin/users/${userId}/subscription`, null, {
      params: {
        plan_id: data.plan_id,
        billing_cycle: data.billing_cycle || 'monthly',
        duration_days: data.duration_days || 30,
      },
    });
    return response.data;
  },

  // Get user detail
  getUserDetail: async (userId: string) => {
    const response = await apiClient.get(`/admin/users/${userId}`);
    return response.data;
  },

  // Create user
  createUser: async (data: {
    name: string;
    email: string;
    password: string;
    role?: string;
  }) => {
    const response = await apiClient.post("/admin/users", data);
    return response.data;
  },

  // Update user
  updateUser: async (userId: string, data: {
    name?: string;
    email?: string;
    timezone?: string;
    role?: string;
  }) => {
    const response = await apiClient.patch(`/admin/users/${userId}`, data);
    return response.data;
  },

  // Delete user (soft delete)
  deleteUser: async (userId: string, permanent: boolean = false) => {
    const response = await apiClient.delete(`/admin/users/${userId}`, {
      params: { permanent },
    });
    return response.data;
  },

  // Restore deleted user
  restoreUser: async (userId: string) => {
    const response = await apiClient.post(`/admin/users/${userId}/restore`);
    return response.data;
  },

  // Reset user password
  resetUserPassword: async (userId: string, newPassword: string) => {
    const response = await apiClient.patch(`/admin/users/${userId}/password`, null, {
      params: { new_password: newPassword },
    });
    return response.data;
  },

  // ============= Device Management =============

  getDevices: async (params?: {
    search?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }) => {
    const response = await apiClient.get("/admin/devices", { params });
    return response.data;
  },

  deleteDevice: async (deviceId: string) => {
    const response = await apiClient.delete(`/admin/devices/${deviceId}`);
    return response.data;
  },

  transferDevice: async (deviceId: string, targetUserId: string) => {
    const response = await apiClient.post(`/admin/devices/${deviceId}/transfer`, {
      target_user_id: targetUserId,
    });
    return response.data;
  },
};
