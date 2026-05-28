import { apiClient } from "@/config/axios-instance";

export interface AssetsMetadata {
  version: string;
  hash: string;
  size: number;
  uploaded_at: string;
  uploaded_by?: string;
  download_url?: string;
}

export interface AssetsUploadResponse {
  status: "success" | "error";
  message: string;
  metadata: AssetsMetadata;
}

export interface AssetsInfoResponse {
  has_assets: boolean;
  message?: string;
  version?: string;
  hash?: string;
  size?: number;
  uploaded_at?: string;
  download_url?: string;
}

export interface AssetsPushResponse {
  status: "success" | "pending" | "error";
  message: string;
  device_online: boolean;
}

/**
 * OTA Assets Service
 * Manages device custom assets (emoji, font, background)
 */
export const otaService = {
  /**
   * Upload assets.bin for a device
   */
  async uploadAssets(
    deviceMacAddress: string,
    file: File
  ): Promise<AssetsUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.post<AssetsUploadResponse>(
      `/ota/assets/upload`,
      formData,
      {
        params: { device_id: deviceMacAddress },
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  },

  /**
   * Get assets info for a device
   */
  async getAssetsInfo(deviceMacAddress: string): Promise<AssetsInfoResponse> {
    const response = await apiClient.get<AssetsInfoResponse>(
      `/ota/assets/${deviceMacAddress}/info`
    );
    return response.data;
  },

  /**
   * Push assets update notification to device
   */
  async pushAssets(deviceMacAddress: string): Promise<AssetsPushResponse> {
    const response = await apiClient.post<AssetsPushResponse>(
      `/ota/assets/${deviceMacAddress}/push`
    );
    return response.data;
  },

  /**
   * Delete assets for a device
   */
  async deleteAssets(
    deviceMacAddress: string
  ): Promise<{ status: string; message: string }> {
    const response = await apiClient.delete<{ status: string; message: string }>(
      `/ota/assets/${deviceMacAddress}`
    );
    return response.data;
  },

  /**
   * Get assets download URL for a device
   */
  getAssetsDownloadUrl(deviceMacAddress: string): string {
    return `/api/v1/ota/assets/${deviceMacAddress}`;
  },
};

export default otaService;
