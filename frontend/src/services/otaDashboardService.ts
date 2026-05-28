import { apiClient } from "@/config/axios-instance";

// ============ Types ============

export interface OTAStats {
  total_devices: number;
  enabled_devices: number;
  disabled_devices: number;
  active_today: number;
  active_this_week: number;
  active_this_month: number;
  total_firmware: number;
  activity_by_day: Record<string, number>;
  board_type_count: Record<string, number>;
  recent_devices: RecentDevice[];
  firmware_stats: FirmwareStats[];
  valid_licenses: number;
  expired_licenses: number;
  unlimited_licenses: number;
  trial_licenses: number;
}

export interface RecentDevice {
  mac: string;
  name: string;
  last_seen: string | null;
  board: string;
  firmware_version: string | null;
  license_type: string;
}

export interface FirmwareStats {
  id: string;
  board_name: string;
  version: string;
  enabled: boolean;
  device_count: number;
  variant: string;
}

export interface LicenseInfo {
  is_valid: boolean;
  activated_at: string | null;
  expires_at: string | null;
  remaining_days: number | null;
  license_type: string;
  message: string;
}

export interface DeviceLicenseUpdate {
  license_type: string;
  license_value?: number | null;
  license_expiration_date?: string | null;
}

export interface DeviceFeaturesUpdate {
  features: Record<string, boolean>;
}

export const DEFAULT_FEATURES: Record<string, boolean> = {
  music: true,
  radio: true,
  weather: true,
  sdCardMusic: true,
  alarm: true,
  reminder: true,
  voiceRecording: true,
  bluetooth: true,
  homeAssistant: true,
};

export const FEATURE_LABELS: Record<string, string> = {
  music: "🎵 Âm nhạc",
  radio: "📻 Radio",
  weather: "🌤️ Thời tiết",
  sdCardMusic: "💾 Nhạc SD Card",
  alarm: "⏰ Báo thức",
  reminder: "📝 Nhắc nhở",
  voiceRecording: "🎙️ Ghi âm",
  bluetooth: "📶 Bluetooth",
  homeAssistant: "🏠 Home Assistant",
};

export const LICENSE_TYPE_LABELS: Record<string, string> = {
  unlimited: "♾️ Không giới hạn",
  days: "📅 Theo ngày",
  months: "📆 Theo tháng",
  years: "📅 Theo năm",
  date: "🎯 Đến ngày cụ thể",
};

// ============ Service ============

export const otaDashboardService = {
  /**
   * Get OTA dashboard statistics
   */
  async getStats(): Promise<OTAStats> {
    const response = await apiClient.get<OTAStats>("/ota-dashboard/stats");
    return response.data;
  },

  /**
   * Get device license info
   */
  async getDeviceLicense(deviceId: string): Promise<LicenseInfo> {
    const response = await apiClient.get<LicenseInfo>(
      `/ota-dashboard/devices/${deviceId}/license`
    );
    return response.data;
  },

  /**
   * Update device license
   */
  async updateDeviceLicense(
    deviceId: string,
    data: DeviceLicenseUpdate
  ): Promise<LicenseInfo> {
    const response = await apiClient.put<LicenseInfo>(
      `/ota-dashboard/devices/${deviceId}/license`,
      data
    );
    return response.data;
  },

  /**
   * Activate device license
   */
  async activateDeviceLicense(deviceId: string): Promise<LicenseInfo> {
    const response = await apiClient.post<LicenseInfo>(
      `/ota-dashboard/devices/${deviceId}/activate`
    );
    return response.data;
  },

  /**
   * Get device features
   */
  async getDeviceFeatures(
    deviceId: string
  ): Promise<{ device_features: Record<string, boolean>; defaults: Record<string, boolean> }> {
    const response = await apiClient.get(
      `/ota-dashboard/devices/${deviceId}/features`
    );
    return response.data;
  },

  /**
   * Update device features
   */
  async updateDeviceFeatures(
    deviceId: string,
    data: DeviceFeaturesUpdate
  ): Promise<{ success: boolean; features: Record<string, boolean> }> {
    const response = await apiClient.put(
      `/ota-dashboard/devices/${deviceId}/features`,
      data
    );
    return response.data;
  },

  /**
   * Update device custom firmware
   */
  async updateDeviceCustomFirmware(
    deviceId: string,
    customFirmware: string | null
  ): Promise<{ success: boolean; custom_firmware: string | null }> {
    const response = await apiClient.put(
      `/ota-dashboard/devices/${deviceId}/custom-firmware`,
      { custom_firmware: customFirmware }
    );
    return response.data;
  },
};

export default otaDashboardService;
