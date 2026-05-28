import { memo, useState, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Button,
  Select,
  Pagination,
  Empty,
  Tag,
  Modal,
  Skeleton,
  Typography,
  Divider
} from "@douyinfe/semi-ui";
import {
  IconPlus,
  IconLayers,
  IconAlertTriangle,
  IconHelpCircle,
  IconLink,
  IconKey,
  IconCheckCircleStroked
} from "@douyinfe/semi-icons";

import type { Provider, ProviderCategory } from "@types";
import {
  useProviderList,
  useCreateProvider,
  useUpdateProvider,
  useDeleteProvider,
  type CreateProviderPayload,
  type ProviderSourceFilter,
} from "@/queries";
import { ProviderCard } from "@/components/ProviderCard";
import { ProviderSheet, PageHead } from "@/components";
import { useToast } from "@/hooks/use-toast";

const { Title, Text, Paragraph } = Typography;

const DEFAULT_PAGE_SIZE = 12;

const CATEGORY_FILTERS: Array<{
  value: ProviderCategory | "all";
  label: string;
}> = [
    { value: "all", label: "All" },
    { value: "LLM", label: "LLM" },
    { value: "VLLM", label: "VLLM" },
    { value: "TTS", label: "TTS" },
    { value: "ASR", label: "ASR" },
    { value: "Memory", label: "Memory" },
    { value: "Intent", label: "Intent" },
  ];

const ProvidersPageComponent = () => {
  const { t } = useTranslation(["providers", "common"]);
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL state
  const page = useMemo(() => {
    const p = searchParams.get("page");
    return p ? parseInt(p, 10) : 1;
  }, [searchParams]);

  const categoryFilter = useMemo(() => {
    const cat = searchParams.get("category");
    return cat as ProviderCategory | null;
  }, [searchParams]);

  const sourceFilter = useMemo(() => {
    const src = searchParams.get("source");
    return (src as ProviderSourceFilter) || "all";
  }, [searchParams]);

  // Local state
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [sheetMode, setSheetMode] = useState<"create" | "update">("create");
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(
    null
  );
  const [guideModalVisible, setGuideModalVisible] = useState(false);

  // Queries & Mutations
  const { data, isLoading, error, refetch } = useProviderList({
    page,
    page_size: DEFAULT_PAGE_SIZE,
    category: categoryFilter ?? undefined,
    source: sourceFilter,
  });

  const { mutateAsync: createProvider, isPending: isCreating } =
    useCreateProvider();
  const { mutateAsync: updateProvider, isPending: isUpdating } =
    useUpdateProvider();
  const { mutate: deleteProvider } = useDeleteProvider();

  // Handlers
  const handleCategoryChange = useCallback(
    (category: ProviderCategory | "all") => {
      const params: Record<string, string> = { page: "1" };
      if (category !== "all") {
        params.category = category;
      }
      if (sourceFilter !== "all") {
        params.source = sourceFilter;
      }
      setSearchParams(params);
    },
    [setSearchParams, sourceFilter]
  );

  const handleSourceChange = useCallback(
    (source: ProviderSourceFilter) => {
      const params: Record<string, string> = { page: "1" };
      if (categoryFilter) {
        params.category = categoryFilter;
      }
      if (source !== "all") {
        params.source = source;
      }
      setSearchParams(params);
    },
    [setSearchParams, categoryFilter]
  );

  const handlePageChange = useCallback(
    (newPage: number) => {
      const params: Record<string, string> = { page: String(newPage) };
      if (categoryFilter) params.category = categoryFilter;
      if (sourceFilter !== "all") params.source = sourceFilter;
      setSearchParams(params);
    },
    [categoryFilter, sourceFilter, setSearchParams]
  );

  const handleOpenCreateSheet = useCallback(() => {
    setSelectedProvider(null);
    setSheetMode("create");
    setIsSheetOpen(true);
  }, []);

  const handleViewProvider = useCallback((provider: Provider) => {
    setSelectedProvider(provider);
    setSheetMode("update");
    setIsSheetOpen(true);
  }, []);

  const handleEditProvider = useCallback((provider: Provider) => {
    setSelectedProvider(provider);
    setSheetMode("update");
    setIsSheetOpen(true);
  }, []);

  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [providerToDelete, setProviderToDelete] = useState<Provider | null>(null);

  const handleDeleteClick = useCallback((provider: Provider) => {
    setProviderToDelete(provider);
    setDeleteModalVisible(true);
  }, []);

  const handleConfirmDelete = useCallback(() => {
    if (providerToDelete) {
      deleteProvider(providerToDelete.id, {
        onSuccess: () => {
          setIsSheetOpen(false);
          setSelectedProvider(null);
          setDeleteModalVisible(false);
          setProviderToDelete(null);
        }
      });
    }
  }, [deleteProvider, providerToDelete]);

  const handleToggleActive = useCallback(
    (provider: Provider) => {
      updateProvider({
        providerId: provider.id,
        payload: { is_active: !provider.is_active },
      });
    },
    [updateProvider]
  );

  const handleDuplicateProvider = useCallback((provider: Provider) => {
    // Close current sheet and open create mode with provider data
    setSelectedProvider(provider);
    setSheetMode("create");
    // Sheet will open in create mode with pre-filled data
  }, []);

  const handleSheetSubmit = useCallback(
    async (payload: CreateProviderPayload) => {
      try {
        // Config-based providers (source="default") don't have ID
        // When "editing" them, we actually CREATE a new copy in the database
        const isUserProvider = selectedProvider?.id && selectedProvider?.source === "user";

        if (sheetMode === "create" || (sheetMode === "update" && !isUserProvider)) {
          // Create new provider (or create copy of config provider)
          await createProvider(payload);
          toast({
            title: t("common:success"),
            description: sheetMode === "create"
              ? t("providers:created_successfully", "Tạo Provider thành công")
              : t("providers:duplicated_successfully", "Đã tạo bản sao Provider thành công"),
            variant: "default",
          });
        } else if (selectedProvider && isUserProvider) {
          // Update existing user provider
          await updateProvider({
            providerId: selectedProvider.id,
            payload: {
              name: payload.name,
              config: payload.config,
              is_active: payload.is_active,
            },
          });
          toast({
            title: t("common:success"),
            description: t("providers:saved_successfully", "Lưu cấu hình thành công"),
            variant: "default",
          });
        }
        setIsSheetOpen(false);
      } catch (error) {
        // Error is typically handled by React Query, but we log it here
        console.error("Failed to save provider:", error);
      }
    },
    [sheetMode, selectedProvider, createProvider, updateProvider, toast, t]
  );

  // Computed values
  const totalProviders = data?.total ?? 0;
  const providers = data?.data ?? [];
  const hasProviders = providers.length > 0;

  // Render loading
  if (isLoading && page === 1 && !categoryFilter) {
    return (
      <div className="space-y-4 p-3 sm:space-y-6 sm:p-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton.Title className="mb-2 w-32" />
            <Skeleton.Paragraph rows={1} className="w-64" />
          </div>
          <Skeleton.Button />
        </div>

        <div className="flex gap-2">
          <Skeleton.Button className="w-16" />
          <Skeleton.Button className="w-16" />
          <Skeleton.Button className="w-16" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <Skeleton.Image className="h-48" />
          <Skeleton.Image className="h-48" />
          <Skeleton.Image className="h-48" />
          <Skeleton.Image className="h-48" />
        </div>
      </div>
    );
  }

  // Render error
  if (error) {
    return (
      <div className="space-y-6 p-6">
        <div>
          <Title heading={2}>{t("providers:providers")}</Title>
          <Text type="tertiary">{t("providers:providers_description")}</Text>
        </div>

        <Empty
          image={<IconAlertTriangle style={{ fontSize: 48, color: 'var(--semi-color-danger)' }} />}
          title={t("providers:error_loading")}
          description={error instanceof Error ? error.message : undefined}
        >
          <Button onClick={() => refetch()}>{t("common:retry")}</Button>
        </Empty>
      </div>
    );
  }

  return (
    <>
      <PageHead
        title="providers:page.title"
        description="providers:page.description"
        translateTitle
        translateDescription
      />
      <div className="space-y-4 p-3 sm:space-y-6 sm:p-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex-1">
            <Title heading={2}>
              {t("providers:providers")}
            </Title>
            <Text type="tertiary" className="mt-2 block">
              {t("providers:providers_description")}
              {totalProviders > 0 && (
                <Tag style={{ marginLeft: 8 }} color="blue">
                  {totalProviders}{" "}
                  {t("providers:provider", { count: totalProviders })}
                </Tag>
              )}
            </Text>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 w-full sm:w-auto">
            <Select
              value={sourceFilter}
              onChange={(value) => handleSourceChange(value as ProviderSourceFilter)}
              placeholder={t("providers:source")}
              style={{ width: 160 }}
              optionList={[
                { value: "all", label: t("providers:all_sources") },
                { value: "user", label: t("providers:my_providers") },
                { value: "config", label: t("providers:default_providers") }
              ]}
            />
            <Button
              onClick={() => setGuideModalVisible(true)}
              icon={<IconHelpCircle />}
              type="tertiary"
            >
              {t("providers:byo_guide", "Hướng dẫn BYO")}
            </Button>
            <Button
              onClick={handleOpenCreateSheet}
              icon={<IconPlus />}
              theme="solid"
            >
              {t("providers:create_provider")}
            </Button>
          </div>
        </div>

        {/* Category Filter — Color-coded tabs */}
        <div className="flex flex-wrap gap-2">
          {CATEGORY_FILTERS.map((cat) => {
            const isActive = categoryFilter === cat.value || (categoryFilter === null && cat.value === "all");
            // Color per category for visual consistency with cards
            const catColors: Record<string, string> = {
              all: "blue", LLM: "indigo", VLLM: "violet", TTS: "cyan", ASR: "amber", Memory: "green", Intent: "red",
            };
            const color = (catColors[cat.value] || "blue") as any;
            return (
              <Tag
                key={cat.value}
                color={isActive ? color : "grey"}
                type={isActive ? "solid" : "ghost"}
                onClick={() => handleCategoryChange(cat.value)}
                style={{ cursor: 'pointer' }}
              >
                {cat.label}
              </Tag>
            );
          })}
        </div>

        {/* Empty State */}
        {!hasProviders && (
          <Empty
            image={<IconLayers style={{ fontSize: 48 }} />}
            title={t("providers:no_providers")}
            description={t("providers:no_providers_description")}
            style={{ padding: 40 }}
          >
            <Button onClick={handleOpenCreateSheet}>
              {t("providers:create_provider")}
            </Button>
          </Empty>
        )}

        {/* Providers Grid */}
        {isLoading && (categoryFilter || page > 1) ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-48 w-full rounded-lg" />
            ))}
          </div>
        ) : (
          hasProviders && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {providers.map((provider, index) => (
                <ProviderCard
                  key={`${provider.source}-${provider.id ?? provider.reference
                    }-${index}`}
                  provider={provider}
                  onView={handleViewProvider}
                  onEdit={handleEditProvider}
                  onDelete={handleDeleteClick}
                  onToggleActive={handleToggleActive}
                />
              ))}
            </div>
          )
        )}

        {/* Pagination */}
        {!isLoading && (data?.total_pages ?? 0) > 1 && (
          <div className="flex justify-center mt-6">
            <Pagination
              total={data?.total}
              pageSize={DEFAULT_PAGE_SIZE}
              currentPage={page}
              onPageChange={handlePageChange}
              showTotal
            />
          </div>
        )}

        {/* Provider Sheet */}
        <ProviderSheet
          open={isSheetOpen}
          onOpenChange={setIsSheetOpen}
          mode={sheetMode}
          provider={selectedProvider}
          initialCategory={categoryFilter}
          onSubmit={handleSheetSubmit}
          onDuplicate={handleDuplicateProvider}
          onDelete={handleDeleteClick}
          isLoading={isCreating || isUpdating}
        />

        <Modal
          visible={deleteModalVisible}
          onCancel={() => setDeleteModalVisible(false)}
          title={t("providers:delete_provider")}
          onOk={handleConfirmDelete}
          okText={t("common:delete")}
          okType="danger"
          cancelText={t("common:cancel")}
          centered
        >
          <Typography.Text>
            {t("providers:delete_provider_confirmation", { name: providerToDelete?.name })}
          </Typography.Text>
        </Modal>

        {/* BYO API Guide Modal */}
        <Modal
          visible={guideModalVisible}
          onCancel={() => setGuideModalVisible(false)}
          title={
            <div className="flex items-center gap-2">
              <IconKey style={{ color: 'var(--semi-color-primary)' }} />
              <span>Hướng Dẫn Thêm API Key (BYO)</span>
            </div>
          }
          footer={
            <Button onClick={() => setGuideModalVisible(false)} theme="solid">
              Đã hiểu
            </Button>
          }
          width={700}
          centered
        >
          <div className="space-y-4">
            <Paragraph>
              <Text strong>BYO (Bring Your Own)</Text> cho phép bạn sử dụng API key riêng để không bị giới hạn bởi quota mặc định.
            </Paragraph>

            <Divider margin={16} />

            {/* DeepSeek */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <IconLink style={{ color: '#4f46e5' }} />
                <Text strong>🔷 DeepSeek (Khuyến nghị)</Text>
                <Tag color="green" size="small">Nhanh nhất</Tag>
              </div>
              <div className="pl-2 space-y-2">
                <Paragraph>
                  <IconCheckCircleStroked style={{ color: 'green' }} /> 1-3M tokens/tháng MIỄN PHÍ
                </Paragraph>
                <ol className="list-decimal pl-5 space-y-1 text-sm">
                  <li>Truy cập: <a href="https://platform.deepseek.com" target="_blank" rel="noreferrer" className="text-blue-500 underline">platform.deepseek.com</a></li>
                  <li>Đăng ký tài khoản (miễn phí)</li>
                  <li>Vào <strong>API Keys</strong> → Tạo key mới</li>
                  <li>Copy key (bắt đầu bằng <code>sk-</code>)</li>
                </ol>
                <div className="bg-gray-100 p-2 rounded text-xs mt-2">
                  <strong>Cấu hình:</strong><br />
                  Base URL: <code>https://api.deepseek.com/v1</code><br />
                  Model: <code>deepseek-chat</code>
                </div>
              </div>
            </div>

            {/* OpenRouter */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <IconLink style={{ color: '#10b981' }} />
                <Text strong>🔷 OpenRouter</Text>
                <Tag color="blue" size="small">Nhiều model</Tag>
              </div>
              <div className="pl-2 space-y-2">
                <Paragraph>
                  <IconCheckCircleStroked style={{ color: 'green' }} /> Truy cập hàng chục model miễn phí
                </Paragraph>
                <ol className="list-decimal pl-5 space-y-1 text-sm">
                  <li>Truy cập: <a href="https://openrouter.ai" target="_blank" rel="noreferrer" className="text-blue-500 underline">openrouter.ai</a></li>
                  <li>Đăng nhập bằng Google/GitHub</li>
                  <li>Vào <strong>Keys</strong> → Create Key</li>
                  <li>Copy key (bắt đầu bằng <code>sk-or-</code>)</li>
                </ol>
                <div className="bg-gray-100 p-2 rounded text-xs mt-2">
                  <strong>Models miễn phí:</strong><br />
                  <code>deepseek/deepseek-r1:free</code><br />
                  <code>qwen/qwen3-30b-a3b:free</code><br />
                  <code>meta-llama/llama-3.3-70b-instruct:free</code>
                </div>
              </div>
            </div>

            {/* HuggingFace */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <IconLink style={{ color: '#f59e0b' }} />
                <Text strong>🔷 HuggingFace</Text>
                <Tag color="orange" size="small">Open-source</Tag>
              </div>
              <div className="pl-2 space-y-2">
                <ol className="list-decimal pl-5 space-y-1 text-sm">
                  <li>Truy cập: <a href="https://huggingface.co" target="_blank" rel="noreferrer" className="text-blue-500 underline">huggingface.co</a></li>
                  <li>Tạo tài khoản miễn phí</li>
                  <li>Vào Settings → <strong>Access Tokens</strong></li>
                  <li>Tạo token với quyền <code>Read</code></li>
                  <li>Copy token (bắt đầu bằng <code>hf_</code>)</li>
                </ol>
              </div>
            </div>

            <Divider margin={16} />

            {/* How to add */}
            <div className="bg-blue-50 p-3 rounded-lg">
              <Text strong className="text-blue-700">Cách thêm Provider bằng mẫu BYO:</Text>
              <ol className="list-decimal pl-5 mt-2 space-y-1 text-sm">
                <li>Click nút <strong>+ Thêm nhà cung cấp</strong></li>
                <li>Chọn category như <strong>LLM</strong>, <strong>TTS</strong>, <strong>ASR</strong></li>
                <li>Chọn một <strong>Mẫu BYO phổ biến</strong> để tự điền type, base URL và model</li>
                <li>Điền <strong>API Key</strong> nếu provider yêu cầu</li>
                <li>Click <strong>Test</strong> để kiểm tra</li>
                <li><strong>Lưu</strong> nếu test thành công!</li>
              </ol>
              <Text type="tertiary" size="small" className="mt-2 block">
                Nhà cung cấp chưa có adapter riêng chỉ dùng được khi họ hỗ trợ OpenAI-compatible API. TTS hiện chỉ giữ Edge TTS và Valtec để tránh cấu hình không chạy được.
              </Text>
            </div>
          </div>
        </Modal>
      </div>
    </>
  );
};

export const ProvidersPage = memo(ProvidersPageComponent);
