/**
 * PluginDetailSheet - Semi Design implementation
 */

import { useTranslation } from "react-i18next";

import type { Plugin } from "@types";
import { SideSheet, Tag, Banner, Divider, Typography, Spin } from "@douyinfe/semi-ui";

const { Title, Text } = Typography;

export interface PluginDetailSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  plugin: Plugin | null;
  isLoading?: boolean;
}

export const PluginDetailSheet = ({
  open,
  onOpenChange,
  plugin,
  isLoading = false,
}: PluginDetailSheetProps) => {
  const { t } = useTranslation(["tools", "common"]);

  if (!plugin) return null;

  return (
    <SideSheet
      title={
        <div className="flex items-center justify-between gap-2">
          <Title heading={5} className="!mb-0 flex-1 truncate">{plugin.name}</Title>
          <Tag color={plugin.enabled ? "green" : "grey"}>
            {plugin.enabled
              ? t("status_enabled", "Enabled")
              : t("status_disabled", "Disabled")}
          </Tag>
        </div>
      }
      visible={open}
      onCancel={() => onOpenChange(false)}
      width={400}
    >
      <Text type="tertiary" className="block mb-4">{plugin.name}</Text>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Spin />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Plugin Info */}
          <div className="space-y-3 rounded-lg border bg-gray-50 dark:bg-gray-800/50 p-4">
            <div>
              <Text type="tertiary" size="small" className="block">
                {t("field_version", "Version")}
              </Text>
              <Text strong>{plugin.version}</Text>
            </div>

            <Divider margin={8} />

            <div>
              <Text type="tertiary" size="small" className="block mb-2">
                {t("field_category", "Category")}
              </Text>
              <Tag>{plugin.category}</Tag>
            </div>

            <Divider margin={8} />

            <div>
              <Text type="tertiary" size="small" className="block">
                {t("field_description", "Description")}
              </Text>
              <Text type="tertiary" className="mt-2 block">
                {plugin.description || "—"}
              </Text>
            </div>
          </div>

          {/* Tools Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Text strong>{t("tools", "Tools")}</Text>
              <Tag size="small">{plugin.tools_count}</Tag>
            </div>

            {plugin.tools && plugin.tools.length > 0 ? (
              <div className="max-h-[300px] space-y-2 overflow-y-auto rounded-lg border bg-gray-50 dark:bg-gray-800/50 p-3">
                {plugin.tools.map((tool) => (
                  <div
                    key={tool.name}
                    className="space-y-1 border-b last:border-0 pb-2 last:pb-0"
                  >
                    <Text strong size="small">{tool.name}</Text>
                    <Text type="tertiary" size="small" className="block">
                      {tool.description || "No description"}
                    </Text>
                    {tool.input_schema && (
                      <details className="text-xs text-gray-500 cursor-pointer">
                        <summary>{t("schema", "Schema")}</summary>
                        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words bg-black/10 rounded p-2 text-xs">
                          {JSON.stringify(tool.input_schema, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <Banner
                type="info"
                description={t("no_tools", "No tools available")}
                closeIcon={null}
              />
            )}
          </div>
        </div>
      )}
    </SideSheet>
  );
};
