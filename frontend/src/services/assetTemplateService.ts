import { apiClient } from "@/config/axios-instance";

export interface AssetTemplate {
  id: string;
  name: string;
  description: string | null;
  board_type: string;
  screen_type: string;
  screen_width: number;
  screen_height: number;
  asset_file_size: number;
  preview_image_base64: string | null;
  wake_word: string | null;
  font_name: string | null;
  emoji_style: string | null;
  is_active: boolean;
  is_default: boolean;
  download_count: number;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string | null;
  download_url?: string;
}

export interface AssetTemplateCreate {
  name: string;
  description?: string;
  board_type: string;
  screen_type: string;
  screen_width: number;
  screen_height: number;
  wake_word?: string;
  font_name?: string;
  emoji_style?: string;
  asset_file_base64?: string;
  preview_image_base64?: string;
  is_default?: boolean;
}

export interface AssetTemplateUpdate {
  name?: string;
  description?: string;
  board_type?: string;
  screen_type?: string;
  screen_width?: number;
  screen_height?: number;
  wake_word?: string;
  font_name?: string;
  emoji_style?: string;
  asset_file_base64?: string;
  preview_image_base64?: string;
  is_active?: boolean;
  is_default?: boolean;
}

export interface AssetTemplateListResponse {
  success: boolean;
  data: AssetTemplate[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BoardTypeInfo {
  board_types: { value: string; label: string }[];
  screen_types: { value: string; label: string }[];
}

export const assetTemplateApi = {
  // List all templates with optional filters
  list: async (params?: {
    page?: number;
    page_size?: number;
    board_type?: string;
    screen_type?: string;
    search?: string;
  }): Promise<AssetTemplateListResponse> => {
    const response = await apiClient.get("/asset-templates", { params });
    return response.data;
  },

  // Get template details
  get: async (id: string): Promise<AssetTemplate> => {
    const response = await apiClient.get(`/asset-templates/${id}`);
    return response.data;
  },

  // Get supported board/screen types
  getBoardTypes: async (): Promise<BoardTypeInfo> => {
    const response = await apiClient.get("/asset-templates/board-types");
    return response.data;
  },

  // Get templates compatible with a device
  getForDevice: async (deviceId: string): Promise<AssetTemplateListResponse> => {
    const response = await apiClient.get(`/asset-templates/for-device/${deviceId}`);
    return response.data;
  },

  // Download template asset file
  download: async (id: string): Promise<Blob> => {
    const response = await apiClient.get(`/asset-templates/${id}/download`, {
      responseType: "blob",
    });
    return response.data;
  },

  // Create new template (admin)
  create: async (data: AssetTemplateCreate): Promise<AssetTemplate> => {
    const response = await apiClient.post("/asset-templates", data);
    return response.data.data;
  },

  // Upload asset file for template (admin)
  uploadFile: async (id: string, file: File): Promise<void> => {
    const formData = new FormData();
    formData.append("file", file);
    await apiClient.post(`/asset-templates/upload-file/${id}`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
  },

  // Update template (admin)
  update: async (id: string, data: AssetTemplateUpdate): Promise<AssetTemplate> => {
    const response = await apiClient.patch(`/asset-templates/${id}`, data);
    return response.data.data;
  },

  // Delete template (admin)
  delete: async (id: string, permanent = false): Promise<void> => {
    await apiClient.delete(`/asset-templates/${id}`, {
      params: { permanent },
    });
  },
};
