import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@config/axios-instance";
import { DEVICE_ENDPOINTS } from "@lib/api";
import type { Device, PaginatedResponse } from "@types";

/**
 * Request payload definitions
 */
export interface DeviceListParams {
  page?: number;
  page_size?: number;
}

export interface ActivateDevicePayload {
  code: string;
}

export interface UpdateDevicePayload {
  device_name?: string;
  board?: string;
  status?: string;
  background_image_url?: string;
  features?: Record<string, boolean>;
}

export interface ActivateDeviceResponse {
  id: string;
  mac_address: string;
  name: string | null;
  board: string | null;
  message: string;
}

export type DeviceListResponse = PaginatedResponse<Device>;

/**
 * Query Keys for device queries
 */
export const deviceQueryKeys = {
  all: ["devices"] as const,
  lists: () => [...deviceQueryKeys.all, "list"] as const,
  list: (params?: DeviceListParams) =>
    [...deviceQueryKeys.lists(), params ?? {}] as const,
  details: () => [...deviceQueryKeys.all, "detail"] as const,
  detail: (deviceId: string) =>
    [...deviceQueryKeys.details(), deviceId] as const,
};

/**
 * API Service Functions using Axios
 */
const deviceAPI = {
  fetchDevices: async (
    params?: DeviceListParams
  ): Promise<DeviceListResponse> => {
    const { data } = await apiClient.get<DeviceListResponse>(
      DEVICE_ENDPOINTS.LIST,
      { params }
    );
    return data;
  },

  fetchDeviceDetail: async (deviceId: string): Promise<Device> => {
    const { data } = await apiClient.get<Device>(
      DEVICE_ENDPOINTS.DETAIL(deviceId)
    );
    return data;
  },

  activateDevice: async (
    payload: ActivateDevicePayload
  ): Promise<ActivateDeviceResponse> => {
    const { data } = await apiClient.post<ActivateDeviceResponse>(
      DEVICE_ENDPOINTS.ACTIVATE,
      payload
    );
    return data;
  },

  deleteDevice: async (deviceId: string): Promise<void> => {
    await apiClient.delete(DEVICE_ENDPOINTS.DELETE(deviceId));
  },

  updateDevice: async (deviceId: string, payload: UpdateDevicePayload): Promise<Device> => {
    const { data } = await apiClient.patch<Device>(
      DEVICE_ENDPOINTS.UPDATE(deviceId),
      payload
    );
    return data;
  },
};

/**
 * Query Hooks
 */
export const useDeviceList = (params?: DeviceListParams) => {
  return useQuery({
    queryKey: deviceQueryKeys.list(params),
    queryFn: () => deviceAPI.fetchDevices(params),
  });
};

export const useDeviceDetail = (deviceId: string, enabled = true) => {
  return useQuery({
    queryKey: deviceQueryKeys.detail(deviceId),
    queryFn: () => deviceAPI.fetchDeviceDetail(deviceId),
    enabled: Boolean(deviceId) && enabled,
  });
};

/**
 * Mutation: Activate Device
 */
export const useActivateDevice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ActivateDevicePayload) =>
      deviceAPI.activateDevice(payload),
    onSuccess: () => {
      // Invalidate device lists to refetch
      queryClient.invalidateQueries({ queryKey: deviceQueryKeys.lists() });
    },
  });
};

/**
 * Mutation: Delete Device
 */
export const useDeleteDevice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (deviceId: string) => deviceAPI.deleteDevice(deviceId),
    onSuccess: () => {
      // Invalidate device lists to refetch
      queryClient.invalidateQueries({ queryKey: deviceQueryKeys.lists() });
    },
  });
};

/**
 * Mutation: Update Device
 */
export const useUpdateDevice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ deviceId, payload }: { deviceId: string; payload: UpdateDevicePayload }) =>
      deviceAPI.updateDevice(deviceId, payload),
    onSuccess: () => {
      // Invalidate device lists to refetch
      queryClient.invalidateQueries({ queryKey: deviceQueryKeys.lists() });
    },
  });
};

// ================================================================
// Agent-Device M2M
// ================================================================

export interface DeviceAgent {
  assignment_id: string;
  agent_id: string;
  agent_name: string;
  is_active: boolean;
  display_order: number;
  assigned_at: string;
}

const agentDeviceAPI = {
  fetchDeviceAgents: async (deviceId: string): Promise<{ success: boolean; data: DeviceAgent[]; total: number }> => {
    const { data } = await apiClient.get(DEVICE_ENDPOINTS.AGENTS(deviceId));
    return data;
  },

  assignAgent: async (deviceId: string, agentId: string, setActive = true) => {
    const { data } = await apiClient.post(DEVICE_ENDPOINTS.ASSIGN_AGENT(deviceId), {
      agent_id: agentId,
      set_active: setActive
    });
    return data;
  },

  unassignAgent: async (deviceId: string, agentId: string) => {
    const { data } = await apiClient.delete(DEVICE_ENDPOINTS.UNASSIGN_AGENT(deviceId, agentId));
    return data;
  },

  switchActiveAgent: async (deviceId: string, agentId: string) => {
    const { data } = await apiClient.put(DEVICE_ENDPOINTS.SWITCH_AGENT(deviceId, agentId));
    return data;
  },
};

export const useDeviceAgents = (deviceId: string, enabled = true) => {
  return useQuery({
    queryKey: [...deviceQueryKeys.detail(deviceId), "agents"],
    queryFn: () => agentDeviceAPI.fetchDeviceAgents(deviceId),
    enabled: Boolean(deviceId) && enabled,
  });
};

export const useAssignAgentToDevice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ deviceId, agentId, setActive = true }: { deviceId: string; agentId: string; setActive?: boolean }) =>
      agentDeviceAPI.assignAgent(deviceId, agentId, setActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deviceQueryKeys.all });
    },
  });
};

export const useUnassignAgentFromDevice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ deviceId, agentId }: { deviceId: string; agentId: string }) =>
      agentDeviceAPI.unassignAgent(deviceId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deviceQueryKeys.all });
    },
  });
};

export const useSwitchActiveAgent = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ deviceId, agentId }: { deviceId: string; agentId: string }) =>
      agentDeviceAPI.switchActiveAgent(deviceId, agentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deviceQueryKeys.all });
    },
  });
};
