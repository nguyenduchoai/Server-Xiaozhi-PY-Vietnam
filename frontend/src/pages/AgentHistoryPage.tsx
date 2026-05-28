/**
 * AgentHistoryPage - Semi Design implementation
 */

import { useState, useEffect, useMemo, useCallback } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowLeft,
  MessageSquare,
  Trash2,
  Clock,
  MoreVertical,
} from "lucide-react";

import {
  useChatSessions,
  useSessionMessages,
  useDeleteAgentMessages,
} from "@/queries/agent-queries";
import { PageHead } from "@/components/PageHead";
import { Button, Tag, Skeleton, Modal, Dropdown, Pagination, Typography } from "@douyinfe/semi-ui";
import { SessionMessages } from "@/components/SessionMessages";
import type { AgentMessage } from "@types";

const { Title, Text } = Typography;

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatTime = (dateString: string) => {
  return new Date(dateString).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
};

const DEFAULT_PAGE_SIZE = 10;

export const AgentHistoryPage = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { t } = useTranslation("agents");

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null
  );
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [messagePage, setMessagePage] = useState(1);
  const [accumulatedMessages, setAccumulatedMessages] = useState<
    AgentMessage[]
  >([]);

  const page = useMemo(() => {
    const p = searchParams.get("page");
    return p ? parseInt(p, 10) : 1;
  }, [searchParams]);

  const {
    data: sessionsData,
    isLoading: isLoadingSessions,
    refetch: refetchSessions,
  } = useChatSessions(agentId || "", {
    page,
    page_size: DEFAULT_PAGE_SIZE,
  });

  const totalPages = sessionsData?.total_pages || 1;

  const { data: messagesData, isLoading: isLoadingMessages } =
    useSessionMessages(
      agentId || "",
      selectedSessionId || "",
      { page: messagePage, page_size: 20 },
      !!selectedSessionId
    );

  useEffect(() => {
    if (selectedSessionId) {
      setMessagePage(1);
      setAccumulatedMessages([]);
    }
  }, [selectedSessionId]);

  useEffect(() => {
    if (messagesData?.data) {
      if (messagePage === 1) {
        setAccumulatedMessages(messagesData.data);
      } else {
        setAccumulatedMessages((prev) => [...prev, ...messagesData.data]);
      }
    }
  }, [messagesData?.data, messagePage]);

  const hasMoreMessages =
    messagesData?.total_pages && messagePage < messagesData.total_pages;

  const handleLoadMore = useCallback((page: number) => {
    setMessagePage(page);
  }, []);

  const { mutateAsync: deleteMessages } = useDeleteAgentMessages(agentId || "");

  useEffect(() => {
    if (
      !selectedSessionId &&
      sessionsData?.data &&
      sessionsData.data.length > 0
    ) {
      setSelectedSessionId(sessionsData.data[0].session_id);
    }
  }, [sessionsData, selectedSessionId]);

  const handlePageChange = useCallback(
    (newPage: number) => {
      setSelectedSessionId(null);
      setSearchParams({ page: String(newPage) });
    },
    [setSearchParams]
  );

  const handleDeleteSession = (sessionId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSessionToDelete(sessionId);
    setDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!agentId || !sessionToDelete) return;

    try {
      if (sessionToDelete === "ALL") {
        await deleteMessages(undefined);
      } else {
        await deleteMessages(sessionToDelete);
      }

      if (selectedSessionId === sessionToDelete) {
        setSelectedSessionId(null);
      }

      setDeleteConfirmOpen(false);
      setSessionToDelete(null);
      refetchSessions();
    } catch (error) {
      console.error("Failed to delete:", error);
    }
  };

  const handleDeleteAll = () => {
    setSessionToDelete("ALL");
    setDeleteConfirmOpen(true);
  };

  if (!agentId) return null;

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <PageHead
        title={t("history_title", "Chat History")}
        description={t("history_description", "View and manage chat history")}
      />

      <div className="flex-1 flex overflow-hidden border-t min-h-0">
        {/* Sidebar - Session List */}
        <div className="w-80 border-r flex flex-col bg-gray-50 dark:bg-gray-900 overflow-hidden">
          <div className="p-4 border-b space-y-4">
            <div className="flex items-center justify-between">
              <Button
                theme="borderless"
                icon={<ArrowLeft className="h-4 w-4" />}
                onClick={() => navigate(`/agents/${agentId}`)}
              >
                {t("back_to_agent", "Back")}
              </Button>

              {sessionsData?.data && sessionsData.data.length > 0 && (
                <Dropdown
                  trigger="click"
                  position="bottomRight"
                  render={
                    <Dropdown.Menu>
                      <Dropdown.Item
                        type="danger"
                        icon={<Trash2 className="h-4 w-4" />}
                        onClick={handleDeleteAll}
                      >
                        {t("delete_all_history", "Delete All History")}
                      </Dropdown.Item>
                    </Dropdown.Menu>
                  }
                >
                  <Button theme="borderless" icon={<MoreVertical className="h-4 w-4" />} />
                </Dropdown>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {isLoadingSessions ? (
              <div className="p-4 space-y-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton.Paragraph rows={2} />
                  </div>
                ))}
              </div>
            ) : sessionsData?.data?.length === 0 ? (
              <div className="p-8 text-center">
                <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <Text type="tertiary">
                  {t("no_history", "No chat history found")}
                </Text>
              </div>
            ) : (
              <div className="flex flex-col">
                {sessionsData?.data.map((session) => (
                  <button
                    key={session.session_id}
                    onClick={() => setSelectedSessionId(session.session_id)}
                    className={`flex flex-col items-start gap-1 p-4 text-left transition-colors hover:bg-gray-100 dark:hover:bg-gray-800 border-b last:border-0 ${selectedSessionId === session.session_id
                      ? "bg-blue-50 dark:bg-blue-900/20 border-l-4 border-l-blue-500 pl-[13px]"
                      : ""
                      }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <Text strong size="small">
                        {formatDate(session.first_message_at)}
                      </Text>
                    </div>
                    <div className="flex items-center gap-2">
                      <Text type="tertiary" size="small" className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" />
                        {session.message_count}
                      </Text>
                      <span className="text-gray-300">•</span>
                      <Text type="tertiary" size="small" className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTime(session.last_message_at)}
                      </Text>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Pagination */}
          {!isLoadingSessions && totalPages > 1 && (
            <div className="p-4 border-t flex-shrink-0 flex justify-center">
              <Pagination
                total={totalPages * DEFAULT_PAGE_SIZE}
                pageSize={DEFAULT_PAGE_SIZE}
                currentPage={page}
                onChange={handlePageChange}
              />
            </div>
          )}
        </div>

        {/* Main Content - Messages */}
        <div className="flex-1 flex flex-col bg-background overflow-hidden">
          {selectedSessionId ? (
            <>
              <div className="h-14 border-b flex items-center justify-between px-6 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <Title heading={5} className="!mb-0">
                    {t("session_detail", "Session Detail")}
                  </Title>
                  <Tag size="small">
                    {selectedSessionId.slice(0, 8)}...
                  </Tag>
                </div>
                <Button
                  theme="borderless"
                  type="danger"
                  icon={<Trash2 className="h-4 w-4" />}
                  onClick={() => handleDeleteSession(selectedSessionId)}
                >
                  {t("delete_session", "Delete Session")}
                </Button>
              </div>

              <div className="flex-1 overflow-hidden">
                <SessionMessages
                  agentId={agentId || ""}
                  sessionId={selectedSessionId || ""}
                  onLoadMore={handleLoadMore}
                  hasMore={hasMoreMessages || false}
                  isLoading={isLoadingMessages}
                  messages={accumulatedMessages}
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <Text type="tertiary">
                  {t("select_session", "Select a session to view messages")}
                </Text>
              </div>
            </div>
          )}
        </div>
      </div>

      <Modal
        title={
          sessionToDelete === "ALL"
            ? t("delete_all_confirm_title", "Delete all history?")
            : t("delete_session_confirm_title", "Delete this session?")
        }
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
            >
              {t("delete")}
            </Button>
          </div>
        }
      >
        <Text type="tertiary">
          {sessionToDelete === "ALL"
            ? t(
              "delete_all_confirm_desc",
              "This action cannot be undone. All chat history for this agent will be permanently deleted."
            )
            : t(
              "delete_session_confirm_desc",
              "This action cannot be undone. This chat session will be permanently deleted."
            )}
        </Text>
      </Modal>
    </div>
  );
};
