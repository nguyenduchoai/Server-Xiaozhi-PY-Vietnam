/**
 * Hardware Types Service
 * 
 * Centralized service for Board Types and Screen Types management.
 * Used by Devices, Asset Templates, and Firmware OTA modules.
 */

import { apiClient } from "@/config/axios-instance";

// =============================================================================
// Types
// =============================================================================

export interface BoardType {
  id: number;
  code: string;
  name: string;
  description?: string;
  chip_family: string;
  flash_size_mb: number;
  psram_size_mb: number;
  is_active: boolean;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
}

export interface ScreenType {
  id: number;
  code: string;
  name: string;
  description?: string;
  driver: string;
  width: number;
  height: number;
  color_depth: number;
  is_active: boolean;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
}

export interface HardwareTypesResponse {
  board_types: BoardType[];
  screen_types: ScreenType[];
}

export interface BoardTypeCreate {
  code: string;
  name: string;
  description?: string;
  chip_family?: string;
  flash_size_mb?: number;
  psram_size_mb?: number;
  is_active?: boolean;
  sort_order?: number;
}

export interface BoardTypeUpdate {
  code?: string;
  name?: string;
  description?: string;
  chip_family?: string;
  flash_size_mb?: number;
  psram_size_mb?: number;
  is_active?: boolean;
  sort_order?: number;
}

export interface ScreenTypeCreate {
  code: string;
  name: string;
  description?: string;
  driver?: string;
  width?: number;
  height?: number;
  color_depth?: number;
  is_active?: boolean;
  sort_order?: number;
}

export interface ScreenTypeUpdate {
  code?: string;
  name?: string;
  description?: string;
  driver?: string;
  width?: number;
  height?: number;
  color_depth?: number;
  is_active?: boolean;
  sort_order?: number;
}

// =============================================================================
// API Functions
// =============================================================================

export const hardwareTypesApi = {
  /**
   * Get all hardware types (board types and screen types)
   */
  getAll: async (activeOnly: boolean = true): Promise<HardwareTypesResponse> => {
    const response = await apiClient.get<HardwareTypesResponse>("/hardware-types", {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  /**
   * Get all board types
   */
  getBoardTypes: async (activeOnly: boolean = true): Promise<BoardType[]> => {
    const response = await apiClient.get<BoardType[]>("/hardware-types/boards", {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  /**
   * Get all screen types
   */
  getScreenTypes: async (activeOnly: boolean = true): Promise<ScreenType[]> => {
    const response = await apiClient.get<ScreenType[]>("/hardware-types/screens", {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  /**
   * Get a single board type by ID
   */
  getBoardType: async (id: number): Promise<BoardType> => {
    const response = await apiClient.get<BoardType>(`/hardware-types/boards/${id}`);
    return response.data;
  },

  /**
   * Get a single screen type by ID
   */
  getScreenType: async (id: number): Promise<ScreenType> => {
    const response = await apiClient.get<ScreenType>(`/hardware-types/screens/${id}`);
    return response.data;
  },

  /**
   * Create a new board type (admin only)
   */
  createBoardType: async (data: BoardTypeCreate): Promise<BoardType> => {
    const response = await apiClient.post<BoardType>("/hardware-types/boards", data);
    return response.data;
  },

  /**
   * Create a new screen type (admin only)
   */
  createScreenType: async (data: ScreenTypeCreate): Promise<ScreenType> => {
    const response = await apiClient.post<ScreenType>("/hardware-types/screens", data);
    return response.data;
  },

  /**
   * Update a board type (admin only)
   */
  updateBoardType: async (id: number, data: BoardTypeUpdate): Promise<BoardType> => {
    const response = await apiClient.patch<BoardType>(`/hardware-types/boards/${id}`, data);
    return response.data;
  },

  /**
   * Update a screen type (admin only)
   */
  updateScreenType: async (id: number, data: ScreenTypeUpdate): Promise<ScreenType> => {
    const response = await apiClient.patch<ScreenType>(`/hardware-types/screens/${id}`, data);
    return response.data;
  },

  /**
   * Delete a board type (admin only)
   */
  deleteBoardType: async (id: number): Promise<void> => {
    await apiClient.delete(`/hardware-types/boards/${id}`);
  },

  /**
   * Delete a screen type (admin only)
   */
  deleteScreenType: async (id: number): Promise<void> => {
    await apiClient.delete(`/hardware-types/screens/${id}`);
  },

  /**
   * Seed default hardware types (admin only)
   */
  seedDefaults: async (): Promise<{ message: string; boards_created: number; screens_created: number }> => {
    const response = await apiClient.post<{ message: string; boards_created: number; screens_created: number }>(
      "/hardware-types/seed-defaults"
    );
    return response.data;
  },
};

export default hardwareTypesApi;
