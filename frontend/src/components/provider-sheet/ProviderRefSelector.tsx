/**
 * ProviderRefSelector - Native HTML select for debugging
 * This is a simplified version to test if the issue is with Semi Design
 */

import { useTranslation } from "react-i18next";

import { useProviderList } from "@/queries/provider-queries";
import { useProviderSheetStore } from "@/store/provider-sheet.store";
import { Typography } from "@douyinfe/semi-ui";
import type { ProviderCategory, ProviderField } from "@types";

const { Text } = Typography;

interface ProviderRefSelectorProps {
  field: ProviderField;
  providerCategory: ProviderCategory;
  disabled?: boolean;
}

export function ProviderRefSelector({
  field,
  providerCategory,
  disabled = false,
}: ProviderRefSelectorProps) {
  const { t } = useTranslation(["common", "providers"]);
  const { formValues, setFieldValue, errors } = useProviderSheetStore();

  const { data: providersData, isLoading } = useProviderList({
    category: providerCategory,
    source: "all",
  });

  // Fallback LLM providers from config.yml (in case API doesn't return data)
  const fallbackLLMProviders = [
    { name: "OpenAI_GPT4", type: "openai" },
    { name: "GoogleGemini", type: "gemini" },
    { name: "DeepSeek_V3", type: "openai" },
    { name: "OpenRouter_DeepSeek_R1", type: "openai" },
    { name: "OpenRouter_Qwen3_30B", type: "openai" },
    { name: "OpenRouter_Qwen3_235B", type: "openai" },
  ];

  const providers = providersData?.data ?? [];
  const selectedValue = formValues[field.name] as string | undefined;
  const error = errors[field.name];

  // Use fallback for LLM category if API returns empty
  const effectiveProviders = providers.length > 0
    ? providers
    : (providerCategory === "LLM" ? fallbackLLMProviders : []);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setFieldValue(field.name, value);
  };

  return (
    <div className="space-y-2">
      <Text strong size="small">
        {field.label}
        {field.required && <span className="ml-1 text-red-500">*</span>}
      </Text>

      {/* Using native HTML select for debugging */}
      <select
        className="w-full p-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        value={selectedValue || ""}
        onChange={handleChange}
        disabled={disabled || isLoading}
      >
        <option value="">
          {isLoading ? "Loading..." : t("providers:select_provider", "Select provider...")}
        </option>
        {effectiveProviders.map((provider) => (
          <option key={provider.name} value={provider.name}>
            {provider.name} ({provider.type})
          </option>
        ))}
      </select>

      {error && <Text type="danger" size="small">{error}</Text>}
    </div>
  );
}
