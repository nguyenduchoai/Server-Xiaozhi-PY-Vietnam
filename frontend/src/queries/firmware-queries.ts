import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  firmwareService,
  type Firmware,
  type FirmwareList,
  type FirmwareUploadParams,
  type FirmwareUpdateParams,
  type Deployment,
  type DeploymentList,
  type DeploymentCreateParams,
  type DeploymentUpdateParams,
  type BoardType,
  type DeploymentStatus,
} from "@/services/firmwareService";

/**
 * Query Keys for firmware queries
 */
export const firmwareQueryKeys = {
  all: ["firmware"] as const,
  lists: () => [...firmwareQueryKeys.all, "list"] as const,
  list: (params?: { page?: number; board_type?: BoardType; is_active?: boolean }) =>
    [...firmwareQueryKeys.lists(), params ?? {}] as const,
  details: () => [...firmwareQueryKeys.all, "detail"] as const,
  detail: (id: string) => [...firmwareQueryKeys.details(), id] as const,
  
  // Deployment keys
  deployments: () => [...firmwareQueryKeys.all, "deployments"] as const,
  deploymentList: (params?: { page?: number; status?: DeploymentStatus; firmware_id?: string }) =>
    [...firmwareQueryKeys.deployments(), "list", params ?? {}] as const,
  deployment: (id: string) => [...firmwareQueryKeys.deployments(), id] as const,
};

// ============ Firmware Hooks ============

/**
 * Hook to fetch firmware list
 */
export function useFirmwareList(params?: {
  page?: number;
  page_size?: number;
  board_type?: BoardType;
  is_active?: boolean;
}) {
  return useQuery<FirmwareList, Error>({
    queryKey: firmwareQueryKeys.list(params),
    queryFn: () => firmwareService.listFirmware(params),
  });
}

/**
 * Hook to fetch firmware details
 */
export function useFirmwareDetail(id: string, enabled = true) {
  return useQuery<Firmware, Error>({
    queryKey: firmwareQueryKeys.detail(id),
    queryFn: () => firmwareService.getFirmware(id),
    enabled: !!id && enabled,
  });
}

/**
 * Hook to upload firmware
 */
export function useUploadFirmware() {
  const queryClient = useQueryClient();
  
  return useMutation<Firmware, Error, FirmwareUploadParams>({
    mutationFn: (params) => firmwareService.uploadFirmware(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: firmwareQueryKeys.lists() });
    },
  });
}

/**
 * Hook to update firmware metadata
 */
export function useUpdateFirmware() {
  const queryClient = useQueryClient();
  
  return useMutation<Firmware, Error, { id: string; params: FirmwareUpdateParams }>({
    mutationFn: ({ id, params }) => firmwareService.updateFirmware(id, params),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: firmwareQueryKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: firmwareQueryKeys.lists() });
    },
  });
}

/**
 * Hook to delete firmware
 */
export function useDeleteFirmware() {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, string>({
    mutationFn: (id) => firmwareService.deleteFirmware(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: firmwareQueryKeys.lists() });
    },
  });
}

// ============ Deployment Hooks ============

/**
 * Hook to fetch deployment list
 */
export function useDeploymentList(params?: {
  page?: number;
  page_size?: number;
  status?: DeploymentStatus;
  firmware_id?: string;
}) {
  return useQuery<DeploymentList, Error>({
    queryKey: firmwareQueryKeys.deploymentList(params),
    queryFn: () => firmwareService.listDeployments(params),
  });
}

/**
 * Hook to fetch deployment details
 */
export function useDeploymentDetail(id: string, enabled = true) {
  return useQuery<Deployment, Error>({
    queryKey: firmwareQueryKeys.deployment(id),
    queryFn: () => firmwareService.getDeployment(id),
    enabled: !!id && enabled,
  });
}

/**
 * Hook to create deployment
 */
export function useCreateDeployment() {
  const queryClient = useQueryClient();
  
  return useMutation<Deployment, Error, DeploymentCreateParams>({
    mutationFn: (params) => firmwareService.createDeployment(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: firmwareQueryKeys.deployments() });
    },
  });
}

/**
 * Hook to update deployment (pause, resume, cancel)
 */
export function useUpdateDeployment() {
  const queryClient = useQueryClient();
  
  return useMutation<Deployment, Error, { id: string; params: DeploymentUpdateParams }>({
    mutationFn: ({ id, params }) => firmwareService.updateDeployment(id, params),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: firmwareQueryKeys.deployment(variables.id) });
      queryClient.invalidateQueries({ queryKey: firmwareQueryKeys.deployments() });
    },
  });
}
