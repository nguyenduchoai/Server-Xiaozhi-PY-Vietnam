/**
 * Device Control API Service
 * 
 * Provides methods to control devices via MQTT:
 * - Radio control (play, stop, next, prev, volume)
 * - Agent switching
 * - TTS speak commands
 */

const API_BASE = '/api/v1/devices';

// Helper to get authenticated headers
function getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('access_token');
    return {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
}

// Types
export interface RadioControlRequest {
    action: 'play' | 'stop' | 'next' | 'prev' | 'volume';
    station_id?: string;
    volume?: number;
}

export interface AgentSwitchRequest {
    action: 'switch' | 'reload';
    template_id?: string;
}

export interface TTSRequest {
    text: string;
    voice?: string;
}

export interface DeviceControlResponse {
    success: boolean;
    message: string;
    device_id: string;
    mqtt_topic?: string;
}

/**
 * Device Control API methods
 */
export const deviceControlApi = {
    /**
     * Control radio playback on device
     */
    async controlRadio(deviceId: string, command: RadioControlRequest): Promise<DeviceControlResponse> {
        const response = await fetch(`${API_BASE}/${deviceId}/radio`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(command),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to control radio');
        }

        return response.json();
    },

    /**
     * Switch agent/template on device
     */
    async switchAgent(deviceId: string, command: AgentSwitchRequest): Promise<DeviceControlResponse> {
        const response = await fetch(`${API_BASE}/${deviceId}/agent`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(command),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to switch agent');
        }

        return response.json();
    },

    /**
     * Speak text on device via TTS
     */
    async speakText(deviceId: string, command: TTSRequest): Promise<DeviceControlResponse> {
        const response = await fetch(`${API_BASE}/${deviceId}/tts`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(command),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send TTS command');
        }

        return response.json();
    },

    /**
     * Send generic control command
     */
    async sendCommand(
        deviceId: string,
        command: {
            type: 'radio' | 'agent' | 'tts' | 'restart' | 'ping';
            radio?: RadioControlRequest;
            agent?: AgentSwitchRequest;
            tts?: TTSRequest;
        }
    ): Promise<DeviceControlResponse> {
        const response = await fetch(`${API_BASE}/${deviceId}/control`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(command),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send command');
        }

        return response.json();
    },

    /**
     * Ping device to check if online
     */
    async pingDevice(deviceId: string): Promise<DeviceControlResponse> {
        return this.sendCommand(deviceId, { type: 'ping' });
    },

    /**
     * Restart device
     */
    async restartDevice(deviceId: string): Promise<DeviceControlResponse> {
        return this.sendCommand(deviceId, { type: 'restart' });
    },

    /**
     * Send intercom message from one device to another
     * Direct MQTT relay without going through AI
     */
    async sendIntercom(
        fromDeviceId: string,
        toDeviceId: string,
        message: string
    ): Promise<DeviceControlResponse> {
        const response = await fetch(`${API_BASE}/${fromDeviceId}/intercom`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                target_device_id: toDeviceId,
                message: message,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send intercom message');
        }

        return response.json();
    },

    /**
     * Get list of other devices for intercom target selection
     */
    async getOtherDevices(): Promise<Array<{ id: string; name: string; mac_address: string; status: string }>> {
        const response = await fetch(`${API_BASE}?page_size=100`, {
            method: 'GET',
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get devices');
        }

        const data = await response.json();
        // Backend returns { data: [...], total: N, page: N, ... } or { success: true, data: [...] }
        // Ensure we always return an array
        const devices = data.data || data.items || [];
        return Array.isArray(devices) ? devices : [];
    },

    /**
     * Get all intercom targets (own devices + friends' devices)
     */
    async getIntercomTargets(): Promise<Array<{
        id: string;
        name: string;
        mac_address: string;
        type: 'own' | 'friend';
        friend_name?: string;
    }>> {
        const results: Array<{ id: string; name: string; mac_address: string; type: 'own' | 'friend'; friend_name?: string }> = [];

        // Get own devices
        try {
            const ownDevices = await this.getOtherDevices();
            for (const d of ownDevices) {
                results.push({
                    id: d.id,
                    name: (d as any).device_name || d.name || d.mac_address,
                    mac_address: d.mac_address,
                    type: 'own',
                });
            }
        } catch (e) {
            console.error('Failed to load own devices:', e);
        }

        // Get friends' devices  
        try {
            const friendsResponse = await fetch('/api/v1/friends/devices', {
                method: 'GET',
                headers: getAuthHeaders(),
            });
            if (friendsResponse.ok) {
                const friendsData = await friendsResponse.json();
                const friendDevices = friendsData.data || friendsData || [];
                for (const d of friendDevices) {
                    results.push({
                        id: d.id,
                        name: d.device_name || d.mac_address,
                        mac_address: d.mac_address,
                        type: 'friend',
                        friend_name: d.friend_name,
                    });
                }
            }
        } catch (e) {
            console.error('Failed to load friend devices:', e);
        }

        return results;
    },

    /**
     * Send voice intercom - records audio from browser and sends to server
     * Server will: ASR -> AI Parse -> MQTT to target device
     */
    async sendVoiceIntercom(
        fromDeviceId: string,
        formData: FormData
    ): Promise<{ success: boolean; transcription?: string; message: string }> {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch(`${API_BASE}/${fromDeviceId}/voice-intercom`, {
            method: 'POST',
            headers: {
                // Don't set Content-Type for FormData - browser will set it with boundary
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send voice intercom');
        }

        return response.json();
    },
};

export default deviceControlApi;
