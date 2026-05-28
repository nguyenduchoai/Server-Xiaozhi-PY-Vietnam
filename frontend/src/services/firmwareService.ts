import { apiClient } from "@/config/axios-instance";

// ============ Types ============

export type BoardType = "esp32" | "esp32s3" | "esp32c3" | "all";
export type DeploymentStatus = "pending" | "rolling_out" | "completed" | "paused" | "cancelled" | "failed";
export type DeploymentTargetType = "all" | "board" | "user" | "device";

export interface Firmware {
  id: string;
  version: string;
  board_type: BoardType;
  file_name: string;
  checksum: string;
  size: number;
  release_notes?: string;
  is_active: boolean;
  is_latest: boolean;
  download_count: number;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface FirmwareList {
  items: Firmware[];
  total: number;
  page: number;
  page_size: number;
}

export interface FirmwareUploadParams {
  file: File;
  version: string;
  board_type: BoardType;
  release_notes?: string;
  is_active?: boolean;
}

export interface FirmwareUpdateParams {
  release_notes?: string;
  is_active?: boolean;
  is_latest?: boolean;
}

export interface Deployment {
  id: string;
  firmware_id: string;
  firmware_version?: string;
  target_type: DeploymentTargetType;
  target_value?: string;
  status: DeploymentStatus;
  rollout_percentage: number;
  deployed_count: number;
  failed_count: number;
  scheduled_at?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface DeploymentList {
  items: Deployment[];
  total: number;
  page: number;
  page_size: number;
}

export interface DeploymentCreateParams {
  firmware_id: string;
  target_type: DeploymentTargetType;
  target_value?: string;
  rollout_percentage?: number;
  scheduled_at?: string;
}

export interface DeploymentUpdateParams {
  status?: DeploymentStatus;
  rollout_percentage?: number;
}

// ============ Service ============

export const firmwareService = {
  /**
   * Upload new firmware file
   */
  async uploadFirmware(params: FirmwareUploadParams): Promise<Firmware> {
    const formData = new FormData();
    formData.append("file", params.file);
    formData.append("version", params.version);
    formData.append("board_type", params.board_type);
    if (params.release_notes) {
      formData.append("release_notes", params.release_notes);
    }
    if (params.is_active !== undefined) {
      formData.append("is_active", String(params.is_active));
    }

    const response = await apiClient.post<Firmware>("/firmware/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  /**
   * List all firmware versions
   */
  async listFirmware(params?: {
    page?: number;
    page_size?: number;
    board_type?: BoardType;
    is_active?: boolean;
  }): Promise<FirmwareList> {
    const response = await apiClient.get<FirmwareList>("/firmware", {
      params: {
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
        board_type: params?.board_type,
        is_active: params?.is_active,
      },
    });
    return response.data;
  },

  /**
   * Get firmware details
   */
  async getFirmware(id: string): Promise<Firmware> {
    const response = await apiClient.get<Firmware>(`/firmware/${id}`);
    return response.data;
  },

  /**
   * Update firmware metadata
   */
  async updateFirmware(id: string, params: FirmwareUpdateParams): Promise<Firmware> {
    const response = await apiClient.patch<Firmware>(`/firmware/${id}`, params);
    return response.data;
  },

  /**
   * Deactivate firmware
   */
  async deleteFirmware(id: string): Promise<void> {
    await apiClient.delete(`/firmware/${id}`);
  },

  /**
   * Get firmware download URL
   */
  getDownloadUrl(id: string): string {
    return `${apiClient.defaults.baseURL}/firmware/${id}/download`;
  },

  // ============ Deployment Methods ============

  /**
   * Create new deployment
   */
  async createDeployment(params: DeploymentCreateParams): Promise<Deployment> {
    const response = await apiClient.post<Deployment>("/firmware/deployments", params);
    return response.data;
  },

  /**
   * List all deployments
   */
  async listDeployments(params?: {
    page?: number;
    page_size?: number;
    status?: DeploymentStatus;
    firmware_id?: string;
  }): Promise<DeploymentList> {
    const response = await apiClient.get<DeploymentList>("/firmware/deployments", {
      params: {
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
        status: params?.status,
        firmware_id: params?.firmware_id,
      },
    });
    return response.data;
  },

  /**
   * Get deployment details
   */
  async getDeployment(id: string): Promise<Deployment> {
    const response = await apiClient.get<Deployment>(`/firmware/deployments/${id}`);
    return response.data;
  },

  /**
   * Update deployment (pause, resume, cancel)
   */
  async updateDeployment(id: string, params: DeploymentUpdateParams): Promise<Deployment> {
    const response = await apiClient.patch<Deployment>(`/firmware/deployments/${id}`, params);
    return response.data;
  },
};
