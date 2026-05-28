/**
 * DynamicSelectField - Load options from API dynamically
 * 
 * Supports loading:
 * - models from LLM provider APIs (OpenAI, Gemini, Claude)
 * - voices from TTS provider APIs (ElevenLabs)
 */

import { useState, useCallback } from "react";
import { Select, Button, Typography, Input } from "@douyinfe/semi-ui";
import { IconRefresh } from "@douyinfe/semi-icons";
import type { ProviderField } from "@types";
import { useProviderSheetStore } from "@/store/provider-sheet.store";
import apiClient from "@/config/axios-instance";
import { PROVIDER_ENDPOINTS } from "@/lib/api/endpoints";

const { Text } = Typography;

interface DynamicSelectFieldProps {
    field: ProviderField;
    isEditDisabled: boolean;
}

interface DynamicOption {
    id: string;
    name: string;
    description?: string;
    owned_by?: string;
    category?: string;
}

/**
 * Get the API endpoint and response key based on dynamic_source.
 * 
 * Supported sources:
 * - "models" → /providers/models/{type}, response key "models"
 * - "voices" → /providers/voices/{type}, response key "voices"
 */
function getSourceConfig(dynamicSource: string | undefined): {
    getEndpoint: (type: string) => string;
    responseKey: string;
    buttonLabel: string;
    selectPlaceholder: string;
    emptyPlaceholder: string;
    loadedLabel: string;
    customLabel: string;
} {
    switch (dynamicSource) {
        case "voices":
            return {
                getEndpoint: (type: string) => PROVIDER_ENDPOINTS.VOICES(type),
                responseKey: "voices",
                buttonLabel: "Load",
                selectPlaceholder: "Chọn giọng nói",
                emptyPlaceholder: "Bấm Load để tải danh sách giọng",
                loadedLabel: "giọng nói",
                customLabel: "Nhập Voice ID thủ công",
            };
        case "models":
        default:
            return {
                getEndpoint: (type: string) => PROVIDER_ENDPOINTS.MODELS(type),
                responseKey: "models",
                buttonLabel: "Load",
                selectPlaceholder: "Chọn model",
                emptyPlaceholder: "Bấm Load Models để tải danh sách",
                loadedLabel: "models",
                customLabel: "Nhập model thủ công",
            };
    }
}

export function DynamicSelectField({
    field,
    isEditDisabled,
}: DynamicSelectFieldProps) {
    const { formValues, errors, setFieldValue, selectedType } = useProviderSheetStore();
    const value = formValues[field.name] as string;
    const error = errors[field.name];

    const [options, setOptions] = useState<DynamicOption[]>([]);
    const [loading, setLoading] = useState(false);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [hasLoaded, setHasLoaded] = useState(false);
    const [useCustomInput, setUseCustomInput] = useState(false);

    const sourceConfig = getSourceConfig(field.dynamic_source);

    // Check if dependencies are met
    const checkDependencies = useCallback(() => {
        if (!field.depends_on || field.depends_on.length === 0) return true;

        return field.depends_on.every((dep) => {
            const depValue = formValues[dep];
            return depValue !== undefined && depValue !== null && depValue !== "";
        });
    }, [field.depends_on, formValues]);

    const dependenciesMet = checkDependencies();

    // Load options from API
    const loadOptions = useCallback(async () => {
        if (!dependenciesMet) {
            setLoadError("Vui lòng nhập các trường bắt buộc trước");
            return;
        }

        setLoading(true);
        setLoadError(null);

        try {
            const apiKey = formValues.api_key as string | undefined;
            const baseUrl = formValues.base_url as string | undefined;

            // Get provider type from store
            const providerType = selectedType || "openai";

            // Build params - only include non-empty values
            const params: Record<string, string> = {};
            if (apiKey) params.api_key = apiKey;
            if (baseUrl) params.base_url = baseUrl;

            const response = await apiClient.get(
                sourceConfig.getEndpoint(providerType),
                { params }
            );

            if (response.data?.error) {
                setLoadError(response.data.error);
                setOptions([]);
            } else {
                // Use the correct response key based on source
                const items = response.data?.[sourceConfig.responseKey] || [];
                setOptions(items);
                setHasLoaded(true);

                // Auto-select first item if no value set
                if (!value && items.length > 0) {
                    setFieldValue(field.name, items[0].id);
                }
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : `Failed to load ${sourceConfig.loadedLabel}`;
            setLoadError(errorMessage);
            setOptions([]);
        } finally {
            setLoading(false);
        }
    }, [dependenciesMet, formValues, selectedType, value, field.name, setFieldValue, sourceConfig]);

    // Convert options to Semi Select format
    const optionList = options.map((opt) => ({
        value: opt.id,
        label: opt.name || opt.id,
    }));

    const getMissingDependencies = () => {
        if (!field.depends_on) return [];
        return field.depends_on.filter((dep) => {
            const depValue = formValues[dep];
            return depValue === undefined || depValue === null || depValue === "";
        });
    };

    const missingDeps = getMissingDependencies();

    return (
        <div className="space-y-2">
            <Text strong size="small">
                {field.label}
                {field.required && <span className="ml-1 text-red-500">*</span>}
            </Text>

            <div className="flex gap-2">
                {useCustomInput ? (
                    <Input
                        style={{ flex: 1 }}
                        placeholder={field.placeholder || `Nhập ${field.label}`}
                        value={value || ""}
                        onChange={(v) => setFieldValue(field.name, v)}
                        disabled={isEditDisabled}
                    />
                ) : (
                    <Select
                        style={{ flex: 1 }}
                        value={value || ""}
                        onChange={(v) => setFieldValue(field.name, v as string)}
                        disabled={isEditDisabled || !hasLoaded}
                        optionList={optionList}
                        placeholder={
                            loading
                                ? "Đang tải..."
                                : hasLoaded
                                    ? sourceConfig.selectPlaceholder
                                    : sourceConfig.emptyPlaceholder
                        }
                        showClear
                        filter
                    />
                )}

                <Button
                    icon={<IconRefresh spin={loading} />}
                    onClick={loadOptions}
                    disabled={isEditDisabled || loading || !dependenciesMet}
                    loading={loading}
                >
                    {sourceConfig.buttonLabel}
                </Button>
            </div>

            {/* Toggle custom input */}
            <div className="flex items-center gap-2">
                <input
                    type="checkbox"
                    id={`custom-${field.name}`}
                    checked={useCustomInput}
                    onChange={(e) => setUseCustomInput(e.target.checked)}
                    disabled={isEditDisabled}
                />
                <label htmlFor={`custom-${field.name}`} className="text-xs text-gray-500">
                    {sourceConfig.customLabel}
                </label>
            </div>

            {/* Missing dependencies hint */}
            {missingDeps.length > 0 && (
                <Text type="warning" size="small">
                    Cần nhập trước: {missingDeps.join(", ")}
                </Text>
            )}

            {/* Load error */}
            {loadError && (
                <Text type="danger" size="small">
                    {loadError}
                </Text>
            )}

            {/* Items count */}
            {hasLoaded && options.length > 0 && (
                <Text type="tertiary" size="small">
                    Đã tải {options.length} {sourceConfig.loadedLabel}
                </Text>
            )}

            {/* Description */}
            {field.description && (
                <Text type="tertiary" size="small">
                    {field.description}
                </Text>
            )}

            {/* Error */}
            {error && <Text type="danger" size="small">{error}</Text>}
        </div>
    );
}
