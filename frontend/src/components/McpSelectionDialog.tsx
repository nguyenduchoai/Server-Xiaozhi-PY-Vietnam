/**
 * McpSelectionDialog - Semi Design implementation
 */

import { useEffect, useState, useMemo } from "react";
import { useTranslation } from "react-i18next";

import type {
  AgentMcpSelection,
  AvailableMcpServer,
  McpSelectionMode,
  MCPServerReference,
} from "@types";
import { Modal, Button, Input, Checkbox, Radio, Banner, Typography, Spin, Tag } from "@douyinfe/semi-ui";
import { IconSearch } from "@douyinfe/semi-icons";

const { Title, Text } = Typography;

export interface McpSelectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentId?: string;
  agentName?: string;
  currentSelection: AgentMcpSelection | null | undefined;
  availableServers: AvailableMcpServer[];
  isLoading?: boolean;
  isSubmitting?: boolean;
  onSubmit: (
    mode: McpSelectionMode,
    servers: MCPServerReference[]
  ) => Promise<void>;
}

export const McpSelectionDialog = ({
  open,
  onOpenChange,
  agentName = "Agent",
  currentSelection,
  availableServers,
  isLoading = false,
  isSubmitting = false,
  onSubmit,
}: McpSelectionDialogProps) => {
  const { t } = useTranslation(["agents", "common"]);
  const [mode, setMode] = useState<McpSelectionMode>("all");
  const [selectedServers, setSelectedServers] = useState<Set<string>>(
    new Set()
  );
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;

    setError(null);
    if (currentSelection) {
      const mode =
        currentSelection.mcp_selection_mode || currentSelection.mode || "all";
      setMode(mode as McpSelectionMode);
      const servers = new Set<string>();

      if (Array.isArray(currentSelection.servers)) {
        currentSelection.servers.forEach((server) => {
          servers.add(server.reference);
        });
      }

      setSelectedServers(servers);
    } else {
      setMode("all");
      setSelectedServers(new Set());
    }
  }, [open, currentSelection]);

  const filteredServers = useMemo(() => {
    if (!Array.isArray(availableServers)) return [];
    return availableServers.filter(
      (server) =>
        server.name.toLowerCase().includes(search.toLowerCase()) ||
        server.reference.toLowerCase().includes(search.toLowerCase())
    );
  }, [availableServers, search]);

  const handleServerToggle = (reference: string) => {
    setSelectedServers((prev) => {
      const next = new Set(prev);
      if (next.has(reference)) {
        next.delete(reference);
      } else {
        next.add(reference);
      }
      return next;
    });
  };

  const handleSubmit = async () => {
    try {
      setError(null);

      const selectedServerList = Array.from(selectedServers).map(
        (reference) => ({
          reference,
        })
      );

      await onSubmit(mode, selectedServerList as MCPServerReference[]);
      onOpenChange(false);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : t("error_unknown", "Unknown error");
      setError(message);
    }
  };

  const userServers = availableServers.filter((s) => s.source === "user");
  const configServers = availableServers.filter((s) => s.source === "config");

  return (
    <Modal
      title={
        <Title heading={5} className="!mb-0">
          {t("mcp_selection_title", "Manage MCP Servers for {{agent}}", {
            agent: agentName,
          })}
        </Title>
      }
      visible={open}
      onCancel={() => onOpenChange(false)}
      width={700}
      footer={
        <div className="flex justify-end gap-2">
          <Button onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            {t("btn_cancel", "Cancel")}
          </Button>
          <Button
            theme="solid"
            type="primary"
            onClick={handleSubmit}
            loading={isSubmitting}
            disabled={isLoading}
          >
            {t("btn_save_changes", "Save Changes")}
          </Button>
        </div>
      }
    >
      <Text type="tertiary" className="block mb-4">
        {t(
          "mcp_selection_description",
          "Select MCP servers to assign to this agent. User-created and system servers are available."
        )}
      </Text>

      <div className="space-y-6">
        {/* Mode Selection */}
        <div className="space-y-3">
          <Text strong>{t("server_selection_mode", "Selection Mode")}</Text>
          <Radio.Group
            value={mode}
            onChange={(e) => setMode(e.target.value as McpSelectionMode)}
            direction="vertical"
            disabled={isSubmitting}
          >
            <Radio value="all">
              {t(
                "use_all_servers_mode",
                "Use all available MCP servers ({{count}})",
                { count: availableServers.length }
              )}
            </Radio>
            <Radio value="selected">
              {t(
                "use_selected_servers_mode",
                "Use selected servers only ({{count}} selected)",
                { count: selectedServers.size }
              )}
            </Radio>
          </Radio.Group>
        </div>

        {/* Error Alert */}
        {error && (
          <Banner type="danger" description={error} closeIcon={null} />
        )}

        {/* Server Selection - Only visible when "selected" mode */}
        {mode === "selected" && (
          <div className="space-y-3">
            <div className="space-y-2">
              <Text strong size="small">
                {t("search_servers", "Search servers")}
              </Text>
              <Input
                prefix={<IconSearch />}
                placeholder={t("search_placeholder", "Search by name...")}
                value={search}
                onChange={setSearch}
                disabled={isSubmitting || isLoading}
              />
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Spin />
              </div>
            ) : availableServers.length === 0 ? (
              <div className="rounded-lg border border-dashed bg-gray-50 dark:bg-gray-800/50 py-8 text-center">
                <Text type="tertiary">
                  {t("no_servers_available", "No MCP servers available")}
                </Text>
              </div>
            ) : (
              <div className="h-[400px] overflow-y-auto rounded-lg border p-4 space-y-4">
                {/* User Servers Section */}
                {userServers.length > 0 && (
                  <div className="space-y-2">
                    <Text type="tertiary" strong size="small">
                      {t("user_servers", "My Servers")} ({userServers.length})
                    </Text>
                    <div className="space-y-2">
                      {userServers
                        .filter((server) =>
                          filteredServers.some(
                            (s) => s.reference === server.reference
                          )
                        )
                        .map((server) => (
                          <div
                            key={server.reference}
                            className="flex items-start space-x-3 rounded-lg border p-3 hover:bg-gray-50 dark:hover:bg-gray-800"
                          >
                            <Checkbox
                              checked={selectedServers.has(server.reference)}
                              onChange={() =>
                                handleServerToggle(server.reference)
                              }
                              disabled={isSubmitting}
                            />
                            <div className="flex-1 min-w-0">
                              <Text strong>{server.name}</Text>
                              <Text type="tertiary" size="small" className="block">
                                {server.type}
                              </Text>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {/* Config Servers Section */}
                {configServers.length > 0 && (
                  <div className="space-y-2 border-t pt-4">
                    <Text type="tertiary" strong size="small">
                      {t("system_servers", "System Servers")} (
                      {configServers.length})
                    </Text>
                    <div className="space-y-2">
                      {configServers
                        .filter((server) =>
                          filteredServers.some(
                            (s) => s.reference === server.reference
                          )
                        )
                        .map((server) => (
                          <div
                            key={server.reference}
                            className="flex items-start space-x-3 rounded-lg border p-3 hover:bg-gray-50 dark:hover:bg-gray-800"
                          >
                            <Checkbox
                              checked={selectedServers.has(server.reference)}
                              onChange={() =>
                                handleServerToggle(server.reference)
                              }
                              disabled={isSubmitting}
                            />
                            <div className="flex-1 min-w-0">
                              <Text strong>{server.name}</Text>
                              <Text type="tertiary" size="small" className="block">
                                {server.type}
                              </Text>
                            </div>
                            <Tag size="small" color="blue">
                              {t("system", "System")}
                            </Tag>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {filteredServers.length === 0 &&
                  availableServers.length > 0 && (
                    <div className="py-8 text-center">
                      <Text type="tertiary">
                        {t(
                          "no_matching_servers",
                          "No servers match your search"
                        )}
                      </Text>
                    </div>
                  )}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
};
