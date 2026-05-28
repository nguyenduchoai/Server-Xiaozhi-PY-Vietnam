import { memo, useState, useCallback, useMemo, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AlertCircle } from "lucide-react";

import type { ToolSchema, ToolCategory } from "@types";
import { useToolAvailable } from "@/queries";
import toolService, { type UserTool } from "@/services/toolService";
import { ToolCard } from "@/components/ToolCard";
import { UserToolSheet } from "@/components/UserToolSheet";
import { PageHead } from "@/components/PageHead";
import {
  Tabs,
  TabPane,
  Button,
  Tag,
  Card,
  Typography,
  SideSheet,
  Descriptions,
  Empty,
  Skeleton,
  Banner
} from "@douyinfe/semi-ui";
import {
  IconWrench,
  IconSetting,
  IconPlus
} from "@douyinfe/semi-icons";

const { Title, Text, Paragraph } = Typography;

/**
 * Category list for filtering
 */
const CATEGORIES: ToolCategory[] = [
  "weather",
  "music",
  "reminder",
  "news",
  "agent",
  "calendar",
  "iot",
  "other",
];

const ToolsPageComponent = () => {
  const { t } = useTranslation(["tools", "common"]);
  const [searchParams, setSearchParams] = useSearchParams();

  // URL state
  const categoryFilter = useMemo(() => {
    const cat = searchParams.get("category");
    return cat as ToolCategory | null;
  }, [searchParams]);

  const activeTab = useMemo(() => {
    return searchParams.get("tab") || "system";
  }, [searchParams]);

  // Local state
  const [selectedTool, setSelectedTool] = useState<ToolSchema | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [userTools, setUserTools] = useState<UserTool[]>([]);
  const [userToolsLoading, setUserToolsLoading] = useState(false);
  const [userToolSheetOpen, setUserToolSheetOpen] = useState(false);
  const [userToolSheetMode, setUserToolSheetMode] = useState<"create" | "edit" | "view">("create");
  const [selectedUserToolId, setSelectedUserToolId] = useState<string | null>(null);

  // Queries
  const { data: availableData, isLoading, error, refetch } = useToolAvailable();

  // Load user tools
  const loadUserTools = useCallback(async () => {
    setUserToolsLoading(true);
    try {
      const response = await toolService.listUserTools({ page_size: 100 });
      setUserTools(response.data);
    } catch (err) {
      console.error("Failed to load user tools:", err);
    } finally {
      setUserToolsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "configs") {
      loadUserTools();
    }
  }, [activeTab, loadUserTools]);

  // Computed values
  const tools = useMemo(() => {
    if (!availableData?.data) return [];
    if (!categoryFilter) return availableData.data;
    return availableData.data.filter(
      (tool) => tool.category === categoryFilter
    );
  }, [availableData, categoryFilter]);

  const categories = useMemo(() => {
    if (!availableData?.data) return [];
    // Get unique categories from available tools
    const cats = new Set(availableData.data.map((t) => t.category));
    return CATEGORIES.filter((c) => cats.has(c));
  }, [availableData]);

  // Handlers
  const handleCategoryChange = useCallback(
    (category: ToolCategory | "all") => {
      if (category === "all") {
        searchParams.delete("category");
      } else {
        searchParams.set("category", category);
      }
      setSearchParams(searchParams);
    },
    [searchParams, setSearchParams]
  );

  const handleTabChange = useCallback(
    (tab: string) => {
      searchParams.set("tab", tab);
      setSearchParams(searchParams);
    },
    [searchParams, setSearchParams]
  );

  const handleViewDetails = useCallback((tool: ToolSchema) => {
    setSelectedTool(tool);
    setIsDetailOpen(true);
  }, []);

  const handleCreateUserTool = useCallback(() => {
    setSelectedUserToolId(null);
    setUserToolSheetMode("create");
    setUserToolSheetOpen(true);
  }, []);

  const handleEditUserTool = useCallback((toolId: string) => {
    setSelectedUserToolId(toolId);
    setUserToolSheetMode("edit");
    setUserToolSheetOpen(true);
  }, []);

  const handleUserToolSuccess = useCallback(() => {
    loadUserTools();
  }, [loadUserTools]);

  const handleUserToolDelete = useCallback(() => {
    loadUserTools();
  }, [loadUserTools]);

  // Render loading
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <PageHead
          title={t("tools:tools")}
          description={t("tools:tools_description")}
        />
        <div className="flex gap-2 mb-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton.Button key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
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
          title={t("tools:tools")}
          description={t("tools:tools_description")}
        />
        <Banner
          type="danger"
          description={error instanceof Error ? error.message : t("tools:error_loading")}
          icon={<AlertCircle />}
        />
        <Button onClick={() => refetch()}>{t("common:retry")}</Button>
      </div>
    );
  }

  return (
    <>
      <PageHead
        title="tools:page.title"
        description="tools:page.description"
        translateTitle
        translateDescription
      />
      <div className="space-y-6 p-6">

        {/* Tabs */}
        <Tabs
          type="line"
          activeKey={activeTab}
          onChange={handleTabChange}
          tabBarExtraContent={
            activeTab === "configs" ? (
              <Button onClick={handleCreateUserTool} icon={<IconPlus />} theme="solid">
                {t("tools:add_config")}
              </Button>
            ) : null
          }
        >
          <TabPane
            tab={
              <span>
                <IconWrench style={{ marginRight: 8 }} />
                {t("tools:system_tools")}
                {availableData && (
                  <Tag style={{ marginLeft: 8 }} size="small" type="ghost">{availableData.total}</Tag>
                )}
              </span>
            }
            itemKey="system"
          >
            <div className="space-y-4 mt-4">
              {/* Category Filter */}
              <div className="flex flex-wrap gap-2">
                <Tag
                  type={categoryFilter === null ? "solid" : "ghost"}
                  className="cursor-pointer"
                  onClick={() => handleCategoryChange("all")}
                >
                  {t("common:all")}
                </Tag>
                {categories.map((cat) => (
                  <Tag
                    key={cat}
                    type={categoryFilter === cat ? "solid" : "ghost"}
                    className="cursor-pointer capitalize"
                    onClick={() => handleCategoryChange(cat)}
                  >
                    {cat}
                  </Tag>
                ))}
              </div>

              {/* Tools Grid */}
              {tools.length === 0 ? (
                <Empty
                  image={<IconWrench style={{ fontSize: 48 }} />}
                  title={t("tools:no_tools")}
                  description={t("tools:no_tools_description")}
                />
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {tools.map((tool) => (
                    <ToolCard
                      key={tool.name}
                      tool={tool}
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
                <IconSetting style={{ marginRight: 8 }} />
                {t("tools:my_configs")}
                {userTools.length > 0 && (
                  <Tag style={{ marginLeft: 8 }} size="small" type="ghost">{userTools.length}</Tag>
                )}
              </span>
            }
            itemKey="configs"
          >
            <div className="mt-4">
              {userToolsLoading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton.Image key={i} style={{ height: 160 }} />
                  ))}
                </div>
              ) : userTools.length === 0 ? (
                <Empty
                  image={<IconSetting style={{ fontSize: 48 }} />}
                  title={t("tools:no_configs")}
                  description={t("tools:no_configs_description")}
                >
                  <Button onClick={handleCreateUserTool} icon={<IconPlus />}>
                    {t("tools:add_config")}
                  </Button>
                </Empty>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {userTools.map((userTool) => (
                    <div key={userTool.id} onClick={() => handleEditUserTool(userTool.id)}>
                      <Card
                        className="cursor-pointer hover:border-blue-500 transition-colors"
                        bodyStyle={{ padding: 16 }}
                        title={
                          <div className="flex items-center justify-between">
                            <Title heading={6} style={{ margin: 0 }}>{userTool.name}</Title>
                            <Tag color={userTool.is_active ? "green" : "grey"}>
                              {userTool.is_active ? t("common:active") : t("common:inactive")}
                            </Tag>
                          </div>
                        }
                      >
                        <Text type="secondary" size="small" className="mb-2 block">{userTool.tool_name}</Text>
                        <Paragraph ellipsis={{ rows: 2 }} type="tertiary" className="text-sm">
                          {userTool.description || t("common:noDescription")}
                        </Paragraph>
                        <div className="mt-4 pt-4 border-t border-gray-100">
                          <Text type="tertiary" size="small">
                            {t("common:updated")}: {new Date(userTool.updated_at).toLocaleDateString()}
                          </Text>
                        </div>
                      </Card>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabPane>
        </Tabs>

        {/* Tool Details Sheet - Converted to Semi SideSheet */}
        <SideSheet
          title={
            <div className="flex items-center gap-2">
              <IconWrench />
              {selectedTool?.name}
            </div>
          }
          visible={isDetailOpen}
          onCancel={() => setIsDetailOpen(false)}
          width={500}
        >
          {selectedTool && (
            <div className="space-y-6">
              <Paragraph>{selectedTool.description}</Paragraph>

              <div>
                <Title heading={5} className="mb-2">{t("tools:basic_info")}</Title>
                <Descriptions
                  data={[
                    { key: t("tools:tool_name"), value: <Tag>{selectedTool.name}</Tag> },
                    { key: t("tools:category"), value: <Tag>{selectedTool.category}</Tag> },
                  ]}
                  row
                  size="small"
                />
              </div>

              {/* Parameters */}
              {selectedTool.parameters?.properties && (
                <div>
                  <Title heading={5} className="mb-2">{t("tools:parameters")}</Title>
                  <div className="border rounded-lg overflow-hidden">
                    {Object.entries(selectedTool.parameters.properties).map(([name, param], index) => (
                      <div key={name} className={`p-4 ${index !== 0 ? 'border-t' : ''}`}>
                        <div className="flex items-center gap-2 mb-1">
                          <Text strong code>{name}</Text>
                          <Tag size="small">{param.type}</Tag>
                          {selectedTool.parameters?.required?.includes(name) && (
                            <Tag color="red" size="small">{t("common:required")}</Tag>
                          )}
                        </div>
                        {param.description && (
                          <Paragraph className="text-gray-500 mb-1">{param.description}</Paragraph>
                        )}
                        {param.enum && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {param.enum.map((v) => (
                              <Tag key={v} type="ghost" size="small">{v}</Tag>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </SideSheet>

        {/* User Tool Sheet - Kept as is (internal implementation might need update later) */}
        <UserToolSheet
          open={userToolSheetOpen}
          onOpenChange={setUserToolSheetOpen}
          mode={userToolSheetMode}
          toolId={selectedUserToolId || undefined}
          onSuccess={handleUserToolSuccess}
          onDelete={handleUserToolDelete}
        />
      </div>
    </>
  );
};

export const ToolsPage = memo(ToolsPageComponent);
