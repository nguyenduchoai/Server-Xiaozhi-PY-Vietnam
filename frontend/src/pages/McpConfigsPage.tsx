import { useState, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle } from "lucide-react";

import {
  useMcpConfigs,
  useSystemMcpServers,
} from "@/queries";
import { PageHead } from "@/components/PageHead";
import { McpConfigCard } from "@/components";
import { SystemMcpCard } from "@/components/SystemMcpCard";
import { McpConfigSheet } from "@/components/McpConfigSheet";
import { SystemMcpSheet } from "@/components/SystemMcpSheet";
import { HomeAssistantQuickSetup } from "@/components/settings/HomeAssistantQuickSetup";

import {
  Button,
  Skeleton,
  Banner,
  Tabs,
  TabPane,
  Empty
} from "@douyinfe/semi-ui";
import {
  IconPlus,
  IconSetting,
  IconSearch,
  IconHome
} from "@douyinfe/semi-icons";

const McpConfigsPageComponent = () => {
  const { t } = useTranslation(["mcp-configs", "common"]);

  // State
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetMode, setSheetMode] = useState<"create" | "edit" | "view" | null>(
    null
  );
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);
  const [selectedSystemMcpServerName, setSelectedSystemMcpServerName] =
    useState<string | null>(null);
  const [systemMcpSheetOpen, setSystemMcpSheetOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"user" | "system">("user");

  // Queries
  const { data: configsData, isLoading, error, refetch } = useMcpConfigs();
  const { data: systemMcpServersData, isLoading: systemMcpLoading } =
    useSystemMcpServers();


  const configs = useMemo(() => configsData?.data || [], [configsData]);
  const systemMcpServers = useMemo(
    () => systemMcpServersData?.data || [],
    [systemMcpServersData]
  );

  // Handlers
  const handleCreateNew = useCallback(() => {
    setSelectedConfigId(null);
    setSheetMode("create");
    setSheetOpen(true);
  }, []);

  const handleViewDetails = useCallback((configId: string) => {
    setSelectedConfigId(configId);
    setSheetMode("view");
    setSheetOpen(true);
  }, []);

  const handleSheetClose = useCallback(() => {
    setSheetOpen(false);
    setSheetMode(null);
    setSelectedConfigId(null);
  }, []);

  const handleSystemMcpViewDetails = useCallback((serverName: string) => {
    setSelectedSystemMcpServerName(serverName);
    setSystemMcpSheetOpen(true);
  }, []);

  const handleSystemMcpSheetClose = useCallback(() => {
    setSystemMcpSheetOpen(false);
    setSelectedSystemMcpServerName(null);
  }, []);



  // Render loading
  if (isLoading || systemMcpLoading) {
    return (
      <div className="space-y-6 p-6">
        <PageHead
          title={t("page_title", "MCP Configurations")}
          description={t(
            "page_description",
            "Manage MCP server configurations for your agents"
          )}
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton.Image key={i} style={{ height: 200 }} />
          ))}
        </div>
      </div>
    );
  }

  // Render error
  if (error) {
    return (
      <div className="space-y-6 p-6">
        <PageHead
          title={t("page_title", "MCP Configurations")}
          description={t(
            "page_description",
            "Manage MCP server configurations for your agents"
          )}
        />
        <Banner
          type="danger"
          description={t("loading_error", "Failed to load MCP configurations")}
          icon={<AlertCircle />}
        />
        <Button onClick={() => refetch()}>{t("btn_retry", "Retry")}</Button>
      </div>
    );
  }

  // Render configs with tabs
  return (
    <div className="space-y-6 p-6">
      <div className="space-y-2">
        <PageHead
          title={t("page_title", "MCP Configurations")}
          description={t(
            "page_description",
            "Manage MCP server configurations for your agents"
          )}
        />
      </div>

      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          {/* We put tabs and button in same row if possible, but TabPane handles content. 
               So we just put the "New" button outside or use tabBarExtraContent */}
        </div>

        <Tabs
          type="line"
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as "user" | "system")}
          tabBarExtraContent={
            activeTab === "user" ? (
              <Button onClick={handleCreateNew} icon={<IconPlus />} theme="solid">
                {t("create_button", "New Configuration")}
              </Button>
            ) : null
          }
        >
          <TabPane
            tab={
              <span>
                {t("user_mcp", "User MCP")}
                <span className="ml-2 text-xs text-gray-500">({configs.length})</span>
              </span>
            }
            itemKey="user"
          >
            <div className="mt-4">
              <div className="mb-4 text-sm text-gray-500">
                {t(
                  "tabs_user_desc",
                  "User MCP servers are custom configurations you create for your agents"
                )}
              </div>
              {configs.length === 0 ? (
                <Empty
                  image={<IconSetting style={{ fontSize: 48 }} />}
                  title={t("empty_title", "No MCP Configurations")}
                  description={t(
                    "empty_description",
                    "Start by creating a new MCP configuration to get started"
                  )}
                >
                  <Button onClick={handleCreateNew} icon={<IconPlus />}>
                    {t("create_button", "New Configuration")}
                  </Button>
                </Empty>
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {configs.map((config) => (
                    <McpConfigCard
                      key={config.id}
                      config={config}
                      toolsCount={config.tools?.length || 0}
                      onViewDetails={handleViewDetails}
                    />
                  ))}
                </div>
              )}
            </div>
          </TabPane>

          <TabPane
            tab={
              <span>
                {t("system_mcp", "System MCP")}
                <span className="ml-2 text-xs text-gray-500">({systemMcpServers.length})</span>
              </span>
            }
            itemKey="system"
          >
            <div className="mt-4">
              <div className="mb-4 text-sm text-gray-500">
                {t(
                  "tabs_system_desc",
                  "System MCP servers are pre-configured by your administrator"
                )}
              </div>
              {systemMcpServers.length === 0 ? (
                <Empty
                  image={<IconSearch style={{ fontSize: 48 }} />}
                  title={t("empty_system_mcp", "No System MCP Servers")}
                  description={t(
                    "empty_system_mcp_description",
                    "No system MCP servers are configured"
                  )}
                />
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {systemMcpServers.map((server) => (
                    <SystemMcpCard
                      key={server.name}
                      server={server}
                      toolsCount={0}
                      onViewDetails={handleSystemMcpViewDetails}
                    />
                  ))}
                </div>
              )}
            </div>
          </TabPane>

          {/* HomeAssistant Quick Setup Tab */}
          <TabPane
            tab={
              <span className="flex items-center gap-1">
                <IconHome />
                {t("homeassistant", "HomeAssistant")}
              </span>
            }
            itemKey="homeassistant"
          >
            <div className="mt-4">
              <div className="mb-4 text-sm text-gray-500">
                {t(
                  "ha_tab_desc",
                  "Quickly configure HomeAssistant integration for smart home control via voice"
                )}
              </div>
              <HomeAssistantQuickSetup />
            </div>
          </TabPane>
        </Tabs>
      </div>

      {/* User MCP Sheet */}
      {sheetMode && (
        <McpConfigSheet
          open={sheetOpen}
          onOpenChange={handleSheetClose}
          mode={sheetMode}
          configId={selectedConfigId || undefined}
          onModeChange={async (newMode, newConfigId) => {
            setSheetMode(newMode);
            if (newConfigId) {
              setSelectedConfigId(newConfigId);
            }
            // Refetch after mode change (especially after create)
            if (newMode === "view") {
              await refetch();
            }
          }}
          onDelete={async (deletedId) => {
            // In the new impl, the sheet might trigger delete or we do it here.
            // If the sheet has a delete button that calls this prop:
            await refetch();
            if (deletedId === selectedConfigId) {
              handleSheetClose();
            }
          }}
        />
      )}

      {/* System MCP Sheet */}
      <SystemMcpSheet
        open={systemMcpSheetOpen}
        onOpenChange={handleSystemMcpSheetClose}
        serverName={selectedSystemMcpServerName || undefined}
      />
    </div>
  );
};

export const McpConfigsPage = McpConfigsPageComponent;
