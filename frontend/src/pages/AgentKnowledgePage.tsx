/**
 * AgentKnowledgePage - Semi Design implementation
 */

import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AlertCircle, ArrowLeft, AlertTriangle } from "lucide-react";

import {
  useKnowledgeBaseItems,
  useCreateKnowledgeEntry,
  useUpdateKnowledgeEntry,
  useDeleteKnowledgeEntry,
  useKnowledgeBaseSearch,
  useIngestFile,
  useIngestUrl,
} from "@/queries";
import { useAgentDetail } from "@/queries/agent-queries";
import {
  KnowledgeEntryList,
  KnowledgeEntryDialog,
  KnowledgeSearchBar,
  KnowledgeAddMenu,
} from "@/components/knowledge";
import { PageHead } from "@/components/PageHead";
import { Button, Skeleton, Modal, Banner, Typography } from "@douyinfe/semi-ui";
import type {
  KnowledgeEntry,
  MemorySector,
  IngestFilePayload,
  IngestUrlPayload,
} from "@/types";

const { Title, Text } = Typography;

const PAGE_SIZE = 20;
const SEARCH_LIMIT = 5;

export const AgentKnowledgePage = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation("agents");

  const [offset, setOffset] = useState(0);
  const [selectedSector, setSelectedSector] = useState<MemorySector | null>(
    null
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<KnowledgeEntry | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [entryToDelete, setEntryToDelete] = useState<string | null>(null);
  const [isKnowledgeBaseDisabled, setIsKnowledgeBaseDisabled] = useState(false);

  const { data: agentData, isLoading: isLoadingAgent } = useAgentDetail(
    agentId || ""
  );
  const {
    data: entriesData,
    isLoading: isLoadingEntries,
    error: entriesError,
  } = useKnowledgeBaseItems(
    agentId || "",
    {
      limit: PAGE_SIZE,
      offset,
      sector: selectedSector || undefined,
    },
    Boolean(agentId) && !searchQuery
  );

  const { mutateAsync: createEntry, isPending: isCreating } =
    useCreateKnowledgeEntry(agentId || "");
  const { mutateAsync: updateEntry, isPending: isUpdating } =
    useUpdateKnowledgeEntry(agentId || "");
  const { mutateAsync: deleteEntry, isPending: isDeleting } =
    useDeleteKnowledgeEntry(agentId || "");
  const {
    mutateAsync: searchEntries,
    data: searchResults,
    isPending: isSearching,
    error: searchError,
  } = useKnowledgeBaseSearch(agentId || "");
  const { mutateAsync: ingestFile, isPending: isIngestingFile } = useIngestFile(
    agentId || ""
  );
  const { mutateAsync: ingestUrl, isPending: isIngestingUrl } = useIngestUrl(
    agentId || ""
  );

  const entries = searchQuery
    ? searchResults?.data?.matches?.map((m) => ({
      id: m.id,
      content: m.content,
      sectors: m.sectors,
      primary_sector: m.primary_sector,
      tags: [],
      metadata: {},
      salience: m.salience,
      last_seen_at: m.last_seen_at,
      created_at: "",
    }))
    : entriesData?.data?.items;
  const totalCount = searchQuery
    ? searchResults?.data?.total
    : entriesData?.data?.total;
  const totalPages = Math.ceil((totalCount || 0) / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const handleSearch = useCallback(
    async (query: string) => {
      setSearchQuery(query);
      if (query && agentId) {
        await searchEntries({
          query,
          k: SEARCH_LIMIT,
          sector: selectedSector || undefined,
        });
      }
    },
    [agentId, searchEntries, selectedSector]
  );

  const handleFilterChange = useCallback((sector: MemorySector | null) => {
    setSelectedSector(sector);
    setOffset(0);
  }, []);

  const handleAddEntry = () => {
    setEditingEntry(null);
    setIsDialogOpen(true);
  };

  const handleEditEntry = (entry: KnowledgeEntry) => {
    setEditingEntry(entry);
    setIsDialogOpen(true);
  };

  const handleDeleteEntry = (entryId: string) => {
    setEntryToDelete(entryId);
    setDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!entryToDelete) return;
    try {
      await deleteEntry(entryToDelete);
    } finally {
      setDeleteConfirmOpen(false);
      setEntryToDelete(null);
    }
  };

  const handleSubmitEntry = async (data: {
    content: string;
    sector: MemorySector;
    tags: string[];
  }) => {
    if (editingEntry) {
      await updateEntry({
        itemId: editingEntry.id,
        payload: {
          content: data.content,
          tags: data.tags,
        },
      });
    } else {
      await createEntry({
        content: data.content,
        sector: data.sector,
        tags: data.tags,
      });
    }
  };

  const handleIngestFile = async (payload: IngestFilePayload) => {
    await ingestFile(payload);
  };

  const handleIngestUrl = async (payload: IngestUrlPayload) => {
    await ingestUrl(payload);
  };

  const handlePageChange = (newPage: number) => {
    setOffset((newPage - 1) * PAGE_SIZE);
  };

  const isAddingKnowledge = isCreating || isIngestingFile || isIngestingUrl;

  useEffect(() => {
    const checkError = (error: any) => {
      if (error?.response?.status === 503) {
        const detail = error?.response?.data?.detail;
        if (detail?.includes("Knowledge Base feature is disabled")) {
          setIsKnowledgeBaseDisabled(true);
        }
      }
    };

    checkError(entriesError);
    checkError(searchError);
  }, [entriesError, searchError]);

  if (!agentId) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <Title heading={4} className="mb-2">
            {t("invalid_agent_id")}
          </Title>
          <Text type="tertiary" className="mb-4 block">
            {t("agent_id_missing")}
          </Text>
          <Button onClick={() => navigate("/agents")}>
            {t("back_to_agents")}
          </Button>
        </div>
      </div>
    );
  }

  if (isLoadingAgent) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton.Avatar />
          <Skeleton.Paragraph rows={1} style={{ width: 200 }} />
        </div>
        <Skeleton.Paragraph rows={1} />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton.Paragraph key={i} rows={3} />
          ))}
        </div>
      </div>
    );
  }

  const agentName = agentData?.agent?.agent_name || t("agent");

  return (
    <>
      <PageHead
        title={`${agentName} - Knowledge Base`}
        description="agents:knowledge.page_description"
        translateDescription
      />
      <div className="p-6 space-y-6">
        {/* Knowledge Base Disabled Warning */}
        {isKnowledgeBaseDisabled && (
          <Banner
            type="warning"
            icon={<AlertTriangle className="h-5 w-5" />}
            title={t("knowledge_base_disabled")}
            description={t("knowledge_base_disabled_desc")}
            closeIcon={null}
          />
        )}

        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Button
              theme="borderless"
              icon={<ArrowLeft className="h-4 w-4" />}
              onClick={() => navigate(`/agents/${agentId}`)}
            />
            <div>
              <Title heading={4} className="!mb-0">{t("knowledge_base")}</Title>
              <Text type="tertiary">{agentName}</Text>
            </div>
          </div>
          <KnowledgeAddMenu
            onAddManual={handleAddEntry}
            onIngestFile={handleIngestFile}
            onIngestUrl={handleIngestUrl}
            isLoading={isAddingKnowledge}
          />
        </div>

        {/* Search & Filter */}
        <KnowledgeSearchBar
          onSearch={handleSearch}
          onFilterChange={handleFilterChange}
          selectedSector={selectedSector}
          isSearching={isSearching}
        />

        {/* Results info */}
        {totalCount !== undefined && totalCount > 0 && (
          <Text type="tertiary">
            {searchQuery
              ? t("search_results_count", { count: totalCount })
              : t("knowledge_entries_count", { count: totalCount })}
          </Text>
        )}

        {/* Entry List */}
        <KnowledgeEntryList
          entries={(entries as KnowledgeEntry[]) || []}
          isLoading={isLoadingEntries || isSearching}
          onEdit={handleEditEntry}
          onDelete={handleDeleteEntry}
          onAddNew={handleAddEntry}
          emptyMessage={
            searchQuery ? t("no_search_results") : t("no_knowledge_entries")
          }
        />

        {/* Pagination */}
        {totalPages > 1 && !searchQuery && (
          <div className="flex items-center justify-center gap-2">
            <Button
              size="small"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage <= 1}
            >
              {t("common:previous")}
            </Button>
            <Text type="tertiary" className="px-4">
              {t("page_info", { current: currentPage, total: totalPages })}
            </Text>
            <Button
              size="small"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
            >
              {t("common:next")}
            </Button>
          </div>
        )}

        {/* Entry Dialog */}
        <KnowledgeEntryDialog
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          entry={editingEntry}
          onSubmit={handleSubmitEntry}
          isLoading={isCreating || isUpdating}
        />

        {/* Delete Confirmation */}
        <Modal
          title={t("delete_entry_confirm")}
          visible={deleteConfirmOpen}
          onCancel={() => setDeleteConfirmOpen(false)}
          footer={
            <div className="flex justify-end gap-2">
              <Button onClick={() => setDeleteConfirmOpen(false)}>
                {t("cancel")}
              </Button>
              <Button
                theme="solid"
                type="danger"
                onClick={handleConfirmDelete}
                loading={isDeleting}
              >
                {t("delete")}
              </Button>
            </div>
          }
        >
          <Text type="tertiary">{t("delete_entry_desc")}</Text>
        </Modal>
      </div>
    </>
  );
};
