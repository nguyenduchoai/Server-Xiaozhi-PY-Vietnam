/**
 * User Tool Service - API client cho quản lý tool configurations
 */
import apiClient from "@/config/axios-instance";

export interface ToolField {
  name: string;
  display_name: string;
  field_type: string;
  description: string;
  required: boolean;
  default: unknown;
  options?: string[];
  validation?: Record<string, unknown>;
}

export interface ToolSchema {
  name: string;
  display_name: string;
  description: string;
  category: string;
  source_type: string;
  parameters: Record<string, unknown>;
  requires_config: boolean;
  fields: ToolField[];
}

export interface UserTool {
  id: string;
  user_id: string;
  tool_name: string;
  name: string;
  description?: string;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface UserToolCreate {
  tool_name: string;
  name: string;
  description?: string;
  config: Record<string, unknown>;
  is_active?: boolean;
}

export interface UserToolUpdate {
  name?: string;
  description?: string;
  config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface ListUserToolsParams {
  tool_name?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SuccessResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

const toolService = {
  /**
   * Get available system tools with schemas
   */
  getAvailableTools: async (q?: string): Promise<{ success: boolean; data: ToolSchema[]; total: number }> => {
    const params = q ? { q } : {};
    const response = await apiClient.get("/tools/available", { params });
    return response.data;
  },

  /**
   * Get tool options for dropdown
   */
  getToolOptions: async (): Promise<{ success: boolean; data: Array<{ value: string; label: string; description: string; category: string }> }> => {
    const response = await apiClient.get("/tools/options");
    return response.data;
  },

  /**
   * Get tool categories
   */
  getCategories: async (): Promise<{ success: boolean; data: Array<{ value: string; label: string }> }> => {
    const response = await apiClient.get("/tools/categories");
    return response.data;
  },

  /**
   * Get schema for a specific tool
   */
  getToolSchema: async (toolName: string): Promise<SuccessResponse<ToolSchema>> => {
    const response = await apiClient.get(`/tools/schemas/${toolName}`);
    return response.data;
  },

  /**
   * List user's tool configurations
   */
  listUserTools: async (params?: ListUserToolsParams): Promise<PaginatedResponse<UserTool>> => {
    const response = await apiClient.get("/tools/configs", { params });
    return response.data;
  },

  /**
   * Create a new tool configuration
   */
  createUserTool: async (data: UserToolCreate): Promise<SuccessResponse<UserTool>> => {
    const response = await apiClient.post("/tools/configs", data);
    return response.data;
  },

  /**
   * Get a specific tool configuration
   */
  getUserTool: async (toolId: string): Promise<SuccessResponse<UserTool>> => {
    const response = await apiClient.get(`/tools/configs/${toolId}`);
    return response.data;
  },

  /**
   * Update a tool configuration
   */
  updateUserTool: async (toolId: string, data: UserToolUpdate): Promise<SuccessResponse<UserTool>> => {
    const response = await apiClient.put(`/tools/configs/${toolId}`, data);
    return response.data;
  },

  /**
   * Delete a tool configuration
   */
  deleteUserTool: async (toolId: string): Promise<void> => {
    await apiClient.delete(`/tools/configs/${toolId}`);
  },
};

export default toolService;
