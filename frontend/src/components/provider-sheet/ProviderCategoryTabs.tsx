/**
 * ProviderCategoryTabs - Semi Design implementation
 */

import { useMemo } from "react";

import type { ProviderCategory, ProviderField } from "@types";
import { useProviderSheetStore } from "@/store/provider-sheet.store";
import { ProviderTypeSelector } from "./ProviderTypeSelector";
import { ProviderConfigForm } from "./ProviderConfigForm";
import { CATEGORY_LIST } from "./types";
import { Tabs, TabPane } from "@douyinfe/semi-ui";

interface ProviderCategoryTabsProps {
  schemaData?: Record<string, Record<string, unknown>>;
  isFormDisabled?: boolean;
}

export function ProviderCategoryTabs({
  schemaData,
  isFormDisabled = false,
}: ProviderCategoryTabsProps) {
  const { selectedCategory, selectedType, selectCategory, mode } =
    useProviderSheetStore();

  const availableCategories = useMemo(() => {
    if (!schemaData) return [];
    return CATEGORY_LIST.filter((cat) => schemaData[cat]);
  }, [schemaData]);

  const selectedFields = useMemo(() => {
    if (!schemaData || !selectedCategory || !selectedType) return [];
    const categoryData = schemaData[selectedCategory];
    if (!categoryData) return [];
    const typeSchema = categoryData[selectedType] as Record<string, unknown>;
    return (typeSchema?.fields ?? []) as ProviderField[];
  }, [schemaData, selectedCategory, selectedType]);

  const isUpdateMode = mode === "update";

  return (
    <Tabs
      activeKey={selectedCategory ?? ""}
      onChange={(key) => {
        if (!isUpdateMode && !isFormDisabled) {
          const category = key as ProviderCategory;
          selectCategory(category);
        }
      }}
      type="line"
    >
      {availableCategories.map((category) => (
        <TabPane
          key={category}
          tab={category}
          itemKey={category}
          disabled={isUpdateMode || isFormDisabled}
        >
          <div className="space-y-6 pt-4">
            {/* Type Selector */}
            <ProviderTypeSelector
              category={category}
              schemaData={schemaData}
              disabled={isFormDisabled}
            />

            {/* Config Form */}
            {(isUpdateMode || selectedType) && (
              <ProviderConfigForm
                selectedFields={selectedFields}
                isEditDisabled={isFormDisabled}
              />
            )}
          </div>
        </TabPane>
      ))}
    </Tabs>
  );
}
