/**
 * ProviderTypeSelector - Semi Design implementation
 */

import { useCallback, useMemo } from "react";

import type { ProviderTypeSchema } from "@types";
import { useProviderSheetStore } from "@/store/provider-sheet.store";
import { Tag, Typography } from "@douyinfe/semi-ui";

const { Text } = Typography;

interface ProviderTypeSelectorProps {
  category: string;
  schemaData?: Record<string, Record<string, unknown>>;
  disabled?: boolean;
}

export function ProviderTypeSelector({
  category,
  schemaData,
  disabled = false,
}: ProviderTypeSelectorProps) {
  const { selectedType, selectType, setFormValues, formValues, mode } =
    useProviderSheetStore();

  const availableTypes = useMemo(() => {
    if (!schemaData || !category) return [];
    const categoryData = schemaData[category];
    return categoryData ? Object.keys(categoryData) : [];
  }, [schemaData, category]);

  const buildDefaults = useCallback(
    (type: string) => {
      const typeSchema = schemaData?.[category]?.[type] as
        | ProviderTypeSchema
        | undefined;

      const defaults: Record<string, unknown> = {};
      typeSchema?.fields?.forEach((field) => {
        if (field.default !== undefined && field.default !== null) {
          defaults[field.name] = field.default;
        }
      });
      return defaults;
    },
    [category, schemaData],
  );

  const applyProviderType = useCallback(
    (type: string) => {
      const currentName = String(formValues.name ?? "");
      selectType(type);
      setFormValues({
        name: currentName,
        ...buildDefaults(type),
      });
    },
    [buildDefaults, formValues.name, selectType, setFormValues],
  );

  if (availableTypes.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Text strong size="small">Loại kỹ thuật</Text>
        <Text type="tertiary" size="small" className="block">
          Dùng khi muốn cấu hình thủ công hoặc nhà cung cấp chỉ tương thích với một adapter có sẵn.
        </Text>
        <div className="flex flex-wrap gap-2">
          {availableTypes.map((type) => {
            const typeSchema = schemaData?.[category]?.[type] as
              | ProviderTypeSchema
              | undefined;
            const isSelected = selectedType === type;
            const isDisabled = mode === "update" || disabled;

            return (
              <div key={type} title={typeSchema?.description}>
                <Tag
                  color={isSelected ? "blue" : "grey"}
                  size="large"
                  className={`px-3 py-1 ${
                    isDisabled
                      ? "cursor-not-allowed opacity-60"
                      : "cursor-pointer hover:opacity-80"
                  }`}
                  onClick={() =>
                    mode === "create" && !disabled && applyProviderType(type)
                  }
                >
                  {typeSchema?.label || type}
                </Tag>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
