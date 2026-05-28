"use client";

/**
 * System MCP Sheet - Semi Design implementation
 */

import { useEffect, useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, ChevronDown, ChevronUp } from "lucide-react";

import type { SystemMcpTestResult } from "@types";
import { useSystemMcpServer, useTestSystemMcpServer } from "@/queries";
import { SideSheet, Button, Input, Tag, Banner, Divider, Typography } from "@douyinfe/semi-ui";

const { Title, Text } = Typography;

interface ToolItemState {
  expanded: boolean;
}

export interface SystemMcpSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverName?: string;
}

export const SystemMcpSheet = ({
  open,
  onOpenChange,
  serverName,
}: SystemMcpSheetProps) => {
  const { t } = useTranslation(["mcp-configs", "common"]);

  // State
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<SystemMcpTestResult | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedTools, setExpandedTools] = useState<Record<string, ToolItemState>>({});

  // Queries
  const { data: serverData } = useSystemMcpServer(
    serverName || "",
    open && !!serverName
  );
  const testMutation = useTestSystemMcpServer();

  const server = serverData?.data;

  // Reset state when sheet opens
  useEffect(() => {
    if (!open) return;

    setError(null);
    setTestResult(null);
    setSearchTerm("");
    setExpandedTools({});
  }, [open]);

  // Tools list with search filter
  const tools = useMemo(() => {
    const toolsList = testResult?.tools || [];
    if (!searchTerm.trim()) return toolsList;
    const term = searchTerm.toLowerCase();
    return toolsList.filter(
      (tool) =>
        tool.name.toLowerCase().includes(term) ||
        tool.description?.toLowerCase().includes(term)
    );
  }, [testResult?.tools, searchTerm]);

  // Handlers
  const handleTestConnection = async () => {
    if (!serverName) return;

    setError(null);
    setTestResult(null);

    try {
      const result = await testMutation.mutateAsync(serverName);
      setTestResult(result);
      if (!result.success) {
        setError(result.message || "Test failed");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Test failed";
      setError(message);
    }
  };

  const toggleToolExpanded = (toolName: string) => {
    setExpandedTools((prev) => ({
      ...prev,
      [toolName]: {
        expanded: !prev[toolName]?.expanded,
      },
    }));
  };

  // Render view mode content
  const renderViewContent = () => {
    if (!server) return null;

    return (
      <div className="h-[calc(100vh-200px)] overflow-y-auto pr-4">
        <div className="space-y-6">
          {/* Server Info */}
          <div className="space-y-4">
            <div>
              <Text type="tertiary" size="small" className="block mb-1">
                {t("name", "Name")}
              </Text>
              <Text strong>{server.name}</Text>
            </div>

            {server.description && (
              <div>
                <Text type="tertiary" size="small" className="block mb-1">
                  {t("description", "Description")}
                </Text>
                <Text type="tertiary" size="small">
                  {server.description}
                </Text>
              </div>
            )}

            <div>
              <Text type="tertiary" size="small" className="block mb-1">
                {t("type", "Type")}
              </Text>
              <Tag>{server.type}</Tag>
            </div>

            <div>
              <Text type="tertiary" size="small" className="block mb-1">
                {t("status", "Status")}
              </Text>
              <Tag color={server.is_active ? "green" : "grey"}>
                {server.is_active
                  ? t("status_active", "Active")
                  : t("status_inactive", "Inactive")}
              </Tag>
            </div>

            {server.type === "http" && server.url && (
              <div>
                <Text type="tertiary" size="small" className="block mb-1">
                  URL
                </Text>
                <Text type="tertiary" size="small" className="break-all">
                  {server.url}
                </Text>
              </div>
            )}

            {server.type === "sse" && server.url && (
              <div>
                <Text type="tertiary" size="small" className="block mb-1">
                  URL
                </Text>
                <Text type="tertiary" size="small" className="break-all">
                  {server.url}
                </Text>
              </div>
            )}

            {server.type === "stdio" && server.command && (
              <div>
                <Text type="tertiary" size="small" className="block mb-1">
                  {t("command", "Command")}
                </Text>
                <Text type="tertiary" size="small">
                  {server.command}
                </Text>
              </div>
            )}
          </div>

          <Divider />

          {/* Test Connection Section */}
          <div className="space-y-3">
            <Text type="tertiary" size="small" className="block">
              {t("test_connection", "Test Connection")}
            </Text>

            {error && (
              <Banner type="danger" description={error} closeIcon={null} />
            )}

            {testResult?.success && (
              <Banner
                type="success"
                description={`${t("connection_success", "Connection successful")} - Found ${testResult.tools?.length || 0} tools`}
                closeIcon={null}
              />
            )}

            {testResult && !testResult.success && (
              <Banner type="danger" description={testResult.message} closeIcon={null} />
            )}

            <Button
              onClick={handleTestConnection}
              disabled={testMutation.isPending}
              className="w-full"
              loading={testMutation.isPending}
              icon={!testMutation.isPending && <RefreshCw className="h-4 w-4" />}
            >
              {testMutation.isPending
                ? t("testing", "Testing")
                : t("test_btn", "Test Connection")}
            </Button>
          </div>

          {/* Tools Section */}
          {testResult?.tools && testResult.tools.length > 0 && (
            <>
              <Divider />

              <div className="space-y-3">
                <Text type="tertiary" size="small" className="block">
                  {t("tools", "Tools")} ({tools.length})
                </Text>

                <Input
                  placeholder={t("search_tools", "Search tools...")}
                  value={searchTerm}
                  onChange={(value) => setSearchTerm(String(value))}
                />

                <div className="space-y-2">
                  {tools.length === 0 ? (
                    <Text type="tertiary" size="small">
                      {t("no_tools_found", "No tools found")}
                    </Text>
                  ) : (
                    tools.map((tool) => (
                      <div
                        key={tool.name}
                        className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900"
                      >
                        <button
                          onClick={() => toggleToolExpanded(tool.name)}
                          className="flex w-full items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-800"
                        >
                          <div className="flex-1 text-left">
                            <Text strong size="small" className="block">{tool.name}</Text>
                            {tool.description && (
                              <Text type="tertiary" size="small" className="line-clamp-1 block">
                                {tool.description}
                              </Text>
                            )}
                          </div>
                          {expandedTools[tool.name]?.expanded ? (
                            <ChevronUp className="h-4 w-4 text-gray-500" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-gray-500" />
                          )}
                        </button>

                        {expandedTools[tool.name]?.expanded && (
                          <>
                            <Divider margin="0" />
                            <div className="space-y-2 p-3">
                              {tool.description && (
                                <div>
                                  <Text type="tertiary" size="small" className="block">
                                    {t("description", "Description")}
                                  </Text>
                                  <Text size="small" className="mt-1 block">
                                    {tool.description}
                                  </Text>
                                </div>
                              )}

                              {tool.inputSchema && (
                                <div>
                                  <Text type="tertiary" size="small" className="block">
                                    {t("input_schema", "Input Schema")}
                                  </Text>
                                  <pre className="mt-1 overflow-auto rounded bg-gray-100 dark:bg-gray-800 p-2 text-xs">
                                    {JSON.stringify(tool.inputSchema, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <SideSheet
      visible={open}
      onCancel={() => onOpenChange(false)}
      title={
        <Title heading={5} className="!mb-0">
          {serverName || t("system_mcp_server", "System MCP Server")}
        </Title>
      }
      width={500}
    >
      <Text type="tertiary" className="block mb-4">
        {t("view_system_mcp_details", "View system MCP server details and test connection")}
      </Text>

      {renderViewContent()}
    </SideSheet>
  );
};
