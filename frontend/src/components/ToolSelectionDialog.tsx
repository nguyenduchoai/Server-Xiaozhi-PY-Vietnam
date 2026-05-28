/**
 * ToolSelectionDialog - Semi Design implementation
 */

import { useEffect, useState, useMemo } from "react";
import { useTranslation } from "react-i18next";

import type {
  AgentToolSelection,
  AvailableMcpTool,
  AvailablePluginTool,
  ToolSelectionMode,
} from "@types";
import { Modal, Button, Input, Checkbox, Radio, Tabs, TabPane, Banner, Typography, Spin } from "@douyinfe/semi-ui";
import { IconSearch } from "@douyinfe/semi-icons";

const { Title, Text } = Typography;

export interface ToolSelectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId?: string;
  currentSelection: AgentToolSelection | null | undefined;
  availableMcpTools: AvailableMcpTool[];
  availablePluginTools: AvailablePluginTool[];
  isLoading?: boolean;
  isSubmitting?: boolean;
  onSubmit: (
    mode: ToolSelectionMode,
    tools: Array<{ type: "server_mcp" | "server_plugin"; name: string }>
  ) => Promise<void>;
}

export const ToolSelectionDialog = ({
  open,
  onOpenChange,
  currentSelection,
  availableMcpTools,
  availablePluginTools,
  isLoading = false,
  isSubmitting = false,
  onSubmit,
}: ToolSelectionDialogProps) => {
  const { t } = useTranslation(["agents", "common"]);
  const [mode, setMode] = useState<ToolSelectionMode>("all");
  const [selectedMcpTools, setSelectedMcpTools] = useState<Set<string>>(
    new Set()
  );
  const [selectedPluginTools, setSelectedPluginTools] = useState<Set<string>>(
    new Set()
  );
  const [mcpSearch, setMcpSearch] = useState("");
  const [pluginSearch, setPluginSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;

    setError(null);
    if (currentSelection) {
      setMode(currentSelection.mode);
      const mcpTools = new Set<string>();
      const pluginTools = new Set<string>();

      if (Array.isArray(currentSelection.tools)) {
        currentSelection.tools.forEach((tool) => {
          if (tool.type === "server_mcp") {
            mcpTools.add(tool.name);
          } else {
            pluginTools.add(tool.name);
          }
        });
      }

      setSelectedMcpTools(mcpTools);
      setSelectedPluginTools(pluginTools);
    } else {
      setMode("all");
      setSelectedMcpTools(new Set());
      setSelectedPluginTools(new Set());
    }
  }, [open, currentSelection]);

  const filteredMcpTools = useMemo(() => {
    if (!Array.isArray(availableMcpTools)) return [];
    return availableMcpTools.filter(
      (tool) =>
        tool.name.toLowerCase().includes(mcpSearch.toLowerCase()) ||
        tool.description.toLowerCase().includes(mcpSearch.toLowerCase())
    );
  }, [availableMcpTools, mcpSearch]);

  const filteredPluginTools = useMemo(() => {
    if (!Array.isArray(availablePluginTools)) return [];
    return availablePluginTools.filter(
      (tool) =>
        tool.name.toLowerCase().includes(pluginSearch.toLowerCase()) ||
        tool.description.toLowerCase().includes(pluginSearch.toLowerCase())
    );
  }, [availablePluginTools, pluginSearch]);

  const handleMcpToolChange = (toolName: string, checked: boolean) => {
    const newSelected = new Set(selectedMcpTools);
    if (checked) {
      newSelected.add(toolName);
    } else {
      newSelected.delete(toolName);
    }
    setSelectedMcpTools(newSelected);
  };

  const handlePluginToolChange = (toolName: string, checked: boolean) => {
    const newSelected = new Set(selectedPluginTools);
    if (checked) {
      newSelected.add(toolName);
    } else {
      newSelected.delete(toolName);
    }
    setSelectedPluginTools(newSelected);
  };

  const handleSubmit = async () => {
    try {
      setError(null);

      const tools: Array<{
        type: "server_mcp" | "server_plugin";
        name: string;
      }> = [];

      if (mode === "all") {
        // Don't send tools if using "all" mode
      } else {
        selectedMcpTools.forEach((toolName) => {
          tools.push({ type: "server_mcp", name: toolName });
        });
        selectedPluginTools.forEach((toolName) => {
          tools.push({ type: "server_plugin", name: toolName });
        });
      }

      await onSubmit(mode, tools);
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
    }
  };

  return (
    <Modal
      title={<Title heading={5} className="!mb-0">{t("manage_agent_tools", "Manage Agent Tools")}</Title>}
      visible={open}
      onCancel={() => onOpenChange(false)}
      width={700}
      footer={
        <div className="flex gap-2">
          <Button
            className="flex-1"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            {t("btn_cancel", "Cancel")}
          </Button>
          <Button
            theme="solid"
            type="primary"
            className="flex-1"
            onClick={handleSubmit}
            loading={isSubmitting}
          >
            {t("btn_save", "Save")}
          </Button>
        </div>
      }
    >
      <Text type="tertiary" className="block mb-4">
        {t("tool_selection_desc", "Choose which tools are available for this agent to use")}
      </Text>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spin />
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {error && (
            <Banner type="danger" description={error} closeIcon={null} />
          )}

          {/* Mode Selection */}
          <div className="space-y-3">
            <Text strong>{t("tool_mode", "Tool Mode")}</Text>
            <Radio.Group
              value={mode}
              onChange={(e) => setMode(e.target.value as ToolSelectionMode)}
              direction="vertical"
            >
              <Radio value="all">
                {t("use_all_tools", "Use all available tools")}
              </Radio>
              <Radio value="selected">
                {t("use_selected_tools", "Use only selected tools")}
              </Radio>
            </Radio.Group>
          </div>

          {/* Tool Selection Tabs */}
          {mode === "selected" && (
            <Tabs type="line">
              <TabPane
                tab={`${t("mcp_tools", "MCP Tools")} (${selectedMcpTools.size})`}
                itemKey="mcp"
              >
                <div className="space-y-3 pt-4">
                  <Input
                    prefix={<IconSearch />}
                    placeholder={t("search_mcp_tools", "Search MCP tools...")}
                    value={mcpSearch}
                    onChange={setMcpSearch}
                  />

                  <div className="max-h-[300px] overflow-y-auto">
                    {filteredMcpTools.length > 0 ? (
                      <div className="space-y-2">
                        {filteredMcpTools.map((tool) => (
                          <div
                            key={tool.name}
                            className="flex items-start space-x-3 py-2"
                          >
                            <Checkbox
                              checked={selectedMcpTools.has(tool.name)}
                              onChange={(e) =>
                                handleMcpToolChange(tool.name, e.target.checked || false)
                              }
                              disabled={isSubmitting}
                            />
                            <div className="flex-1 min-w-0">
                              <Text strong className="text-sm">
                                {tool.name}
                              </Text>
                              <Text type="tertiary" size="small" className="block">
                                {tool.config_name} • {tool.description}
                              </Text>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex items-center justify-center py-8">
                        <Text type="tertiary">
                          {t("no_mcp_tools", "No MCP tools available")}
                        </Text>
                      </div>
                    )}
                  </div>
                </div>
              </TabPane>

              <TabPane
                tab={`${t("plugin_tools", "Plugin Tools")} (${selectedPluginTools.size})`}
                itemKey="plugin"
              >
                <div className="space-y-3 pt-4">
                  <Input
                    prefix={<IconSearch />}
                    placeholder={t("search_plugin_tools", "Search plugin tools...")}
                    value={pluginSearch}
                    onChange={setPluginSearch}
                  />

                  <div className="max-h-[300px] overflow-y-auto">
                    {filteredPluginTools.length > 0 ? (
                      <div className="space-y-2">
                        {filteredPluginTools.map((tool) => (
                          <div
                            key={tool.name}
                            className="flex items-start space-x-3 py-2"
                          >
                            <Checkbox
                              checked={selectedPluginTools.has(tool.name)}
                              onChange={(e) =>
                                handlePluginToolChange(tool.name, e.target.checked || false)
                              }
                              disabled={isSubmitting}
                            />
                            <div className="flex-1 min-w-0">
                              <Text strong className="text-sm">
                                {tool.name}
                              </Text>
                              <Text type="tertiary" size="small" className="block">
                                {tool.plugin_name} • {tool.description}
                              </Text>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex items-center justify-center py-8">
                        <Text type="tertiary">
                          {t("no_plugin_tools", "No plugin tools available")}
                        </Text>
                      </div>
                    )}
                  </div>
                </div>
              </TabPane>
            </Tabs>
          )}
        </div>
      )}
    </Modal>
  );
};
