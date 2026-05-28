/**
 * ProviderToolSelector - Native HTML select for debugging
 * This is a simplified version to test if the issue is with Semi Design
 */

import { useTranslation } from "react-i18next";

import { useProviderSheetStore } from "@/store/provider-sheet.store";
import { useToolOptions } from "@/queries";
import { Typography, Tag } from "@douyinfe/semi-ui";

const { Text } = Typography;

interface ProviderToolSelectorProps {
  disabled?: boolean;
}

export function ProviderToolSelector({
  disabled = false,
}: ProviderToolSelectorProps) {
  const { t } = useTranslation(["common", "providers"]);
  const { selectedTools, setSelectedTools, toggleTool } =
    useProviderSheetStore();

  const { data: toolOptionsData, isLoading: isLoadingTools } =
    useToolOptions(true);

  const toolOptions = toolOptionsData?.data ?? [];

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const options = e.target.options;
    const selected: string[] = [];
    for (let i = 0; i < options.length; i++) {
      if (options[i].selected) {
        selected.push(options[i].value);
      }
    }
    setSelectedTools(selected);
  };

  return (
    <div className="space-y-2">
      <Text strong size="small">
        {t("common:functions", "Functions")}
        <span className="ml-2 text-gray-400 font-normal">
          ({selectedTools.length} {t("common:selected", "selected")})
        </span>
      </Text>

      {/* Using native HTML multi-select for debugging */}
      <select
        className="w-full p-2 border border-gray-300 rounded-md bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        multiple
        size={Math.min(10, toolOptions.length || 5)}
        value={selectedTools}
        onChange={handleChange}
        disabled={disabled || isLoadingTools}
      >
        {toolOptions.map((tool) => (
          <option key={tool.value} value={tool.value}>
            {tool.label}
          </option>
        ))}
      </select>

      <Text type="tertiary" size="small">
        Giữ Ctrl (Windows) hoặc Cmd (Mac) để chọn nhiều
      </Text>

      {/* Show selected tools as tags */}
      {selectedTools.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {selectedTools.map((ref) => {
            const tool = toolOptions.find((t) => t.value === ref);
            return (
              <Tag
                key={ref}
                closable
                onClose={() => !disabled && toggleTool(ref)}
                size="small"
              >
                {tool?.label ?? ref}
              </Tag>
            );
          })}
        </div>
      )}
    </div>
  );
}
