/**
 * Provider API functions
 * Handles provider-related API calls
 */

import apiClient from "@/config/axios-instance";
import { PROVIDER_ENDPOINTS } from "@/lib/api/endpoints";
import type { AxiosResponse } from "axios";

export interface ModelOption {
    id: string;
    name: string;
    description?: string;
    owned_by?: string;
    created_at?: string;
}

export interface GetModelsResponse {
    provider_type: string;
    models: ModelOption[];
    count: number;
    error: string | null;
}

/**
 * Fetch available models from a provider's API
 * 
 * @param providerType - Type of provider (openai, gemini, claude)
 * @param apiKey - API key for the provider  
 * @param baseUrl - Optional base URL for OpenAI-compatible APIs
 */
export async function getProviderModels(
    providerType: string,
    apiKey: string,
    baseUrl?: string
): Promise<AxiosResponse<GetModelsResponse>> {
    const params: Record<string, string> = { api_key: apiKey };
    if (baseUrl) {
        params.base_url = baseUrl;
    }

    return apiClient.get(PROVIDER_ENDPOINTS.MODELS(providerType), { params });
}

export const providerApi = {
    getProviderModels,
};

export default providerApi;
