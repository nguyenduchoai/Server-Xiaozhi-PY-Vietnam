/**
 * AgentHistorySection - 2-Column Chat History Layout for Agent Detail Tabs
 * Left sidebar: Session list | Right: Selected session messages
 */

import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
    useChatSessions,
    useSessionMessages,
    useDeleteAgentMessages,
} from "@/queries/agent-queries";
import { Button, Skeleton, Modal, Typography, Empty, Pagination, Tag } from "@douyinfe/semi-ui";
import { IconDelete } from "@douyinfe/semi-icons";
import { MessageSquare, Clock, Trash2 } from "lucide-react";
import type { AgentMessage } from "@types";
import apiClient from "@config/axios-instance";
import { AGENT_ENDPOINTS } from "@api";

const { Text } = Typography;

/** Lazy voice replay button — fetches the WAV blob via axios (sends Bearer token). */
function MessageAudio({ agentId, messageId }: { agentId: string; messageId: string }) {
    const [audioUrl, setAudioUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        return () => {
            if (audioUrl) URL.revokeObjectURL(audioUrl);
        };
    }, [audioUrl]);

    const loadAudio = async () => {
        if (audioUrl || loading) return;
        setLoading(true);
        try {
            const { data } = await apiClient.get<Blob>(
                AGENT_ENDPOINTS.MESSAGE_AUDIO(agentId, messageId),
                { responseType: "blob" }
            );
            setAudioUrl(URL.createObjectURL(data));
        } catch {
            setAudioUrl(null);
        } finally {
            setLoading(false);
        }
    };

    if (audioUrl) {
        return <audio controls src={audioUrl} className="mt-2 h-8 w-full" />;
    }
    return (
        <Button theme="borderless" size="small" loading={loading} onClick={loadAudio}>
            ▶ Voice
        </Button>
    );
}

const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
    });
};

const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
};

interface AgentHistorySectionProps {
    agentId: string;
}

export function AgentHistorySection({ agentId }: AgentHistorySectionProps) {
    const { t } = useTranslation("agents");
    const [currentPage, setCurrentPage] = useState(1);
    const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
    const [messagePage, setMessagePage] = useState(1);
    const [accumulatedMessages, setAccumulatedMessages] = useState<AgentMessage[]>([]);
    const pageSize = 10;

    const params = useMemo(() => ({ page: currentPage, page_size: pageSize }), [currentPage]);
    const { data, isLoading, refetch } = useChatSessions(agentId, params);
    const { mutateAsync: deleteMessages, isPending: isDeleting } = useDeleteAgentMessages(agentId);

    // Fetch messages for selected session
    const { data: messagesData, isLoading: isLoadingMessages } = useSessionMessages(
        agentId,
        selectedSessionId || "",
        { page: messagePage, page_size: 20 },
        !!selectedSessionId
    );

    const sessions = data?.data || [];
    const totalPages = data?.total_pages || 1;

    // Reset messages when session changes
    useEffect(() => {
        if (selectedSessionId) {
            setMessagePage(1);
            setAccumulatedMessages([]);
        }
    }, [selectedSessionId]);

    // Accumulate messages
    useEffect(() => {
        if (messagesData?.data) {
            if (messagePage === 1) {
                setAccumulatedMessages(messagesData.data);
            } else {
                setAccumulatedMessages(prev => [...prev, ...messagesData.data]);
            }
        }
    }, [messagesData, messagePage]);

    const handleDeleteSession = (sessionId: string, e?: React.MouseEvent) => {
        e?.stopPropagation();
        setSessionToDelete(sessionId);
        setDeleteModalOpen(true);
    };

    const handleConfirmDelete = async () => {
        if (sessionToDelete) {
            try {
                if (sessionToDelete === "ALL") {
                    await deleteMessages(undefined);
                    setSelectedSessionId(null);
                } else {
                    await deleteMessages(sessionToDelete);
                    if (selectedSessionId === sessionToDelete) {
                        setSelectedSessionId(null);
                    }
                }
                refetch();
            } catch (error) {
                console.error("Delete failed:", error);
            }
        }
        setDeleteModalOpen(false);
        setSessionToDelete(null);
    };

    const handleDeleteAll = async () => {
        setSessionToDelete("ALL");
        setDeleteModalOpen(true);
    };

    const loadMoreMessages = () => {
        if (messagesData?.total_pages && messagePage < messagesData.total_pages) {
            setMessagePage(prev => prev + 1);
        }
    };

    if (isLoading) {
        return (
            <div className="flex gap-4 h-[500px]">
                <div className="w-72 space-y-3">
                    {[1, 2, 3, 4, 5].map((i) => (
                        <Skeleton.Paragraph key={i} rows={2} />
                    ))}
                </div>
                <div className="flex-1">
                    <Skeleton.Paragraph rows={10} />
                </div>
            </div>
        );
    }

    if (sessions.length === 0) {
        return (
            <Empty
                title={t("no_history", "Chưa có lịch sử")}
                description={t("no_history_desc", "Chưa có cuộc hội thoại nào được ghi lại")}
            />
        );
    }

    return (
        <div className="flex gap-4 h-[500px]">
            {/* Left Sidebar - Session List */}
            <div className="w-72 flex flex-col border-r pr-4">
                {/* Header */}
                <div className="flex items-center justify-between mb-3 pb-3 border-b">
                    <Text type="tertiary" size="small">
                        {data?.total || sessions.length} {t("sessions", "phiên hội thoại")}
                    </Text>
                    {sessions.length > 0 && (
                        <Button
                            type="danger"
                            theme="light"
                            size="small"
                            icon={<IconDelete />}
                            onClick={handleDeleteAll}
                            loading={isDeleting}
                        >
                            {t("delete_all", "Xóa tất cả")}
                        </Button>
                    )}
                </div>

                {/* Session List */}
                <div className="flex-1 overflow-y-auto space-y-1">
                    {sessions.map((session: any) => (
                        <button
                            key={session.session_id}
                            onClick={() => setSelectedSessionId(session.session_id)}
                            className={`w-full flex flex-col items-start gap-1 p-3 text-left rounded-lg transition-colors ${selectedSessionId === session.session_id
                                ? "bg-blue-50 border-l-4 border-l-blue-500"
                                : "hover:bg-gray-50"
                                }`}
                        >
                            <div className="flex items-center justify-between w-full">
                                <Text strong size="small">
                                    {formatDate(session.first_message_at || session.start_time)}
                                </Text>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                                <MessageSquare className="h-3 w-3" />
                                <span>{session.message_count || 0}</span>
                                <span className="text-gray-300">•</span>
                                <Clock className="h-3 w-3" />
                                <span>{formatTime(session.last_message_at || session.first_message_at)}</span>
                            </div>
                        </button>
                    ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="pt-3 border-t">
                        <Pagination
                            currentPage={currentPage}
                            total={totalPages * pageSize}
                            pageSize={pageSize}
                            onChange={(page) => setCurrentPage(page)}
                            size="small"
                            showTotal
                        />
                    </div>
                )}
            </div>

            {/* Right Content - Messages */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {selectedSessionId ? (
                    <>
                        {/* Header */}
                        <div className="flex items-center justify-between pb-3 border-b mb-3">
                            <Text strong>
                                {t("chat_messages", "Tin nhắn")}
                            </Text>
                            <Button
                                icon={<Trash2 className="h-4 w-4" />}
                                type="danger"
                                theme="borderless"
                                size="small"
                                onClick={(e) => handleDeleteSession(selectedSessionId, e)}
                            >
                                {t("delete_session", "Xóa phiên")}
                            </Button>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                            {isLoadingMessages && accumulatedMessages.length === 0 ? (
                                <Skeleton.Paragraph rows={5} />
                            ) : accumulatedMessages.length > 0 ? (
                                <>
                                    {accumulatedMessages.map((msg: any, idx: number) => (
                                        <div
                                            key={msg.id || idx}
                                            className={`p-3 rounded-lg ${msg.sender === "user" || msg.type === "user"
                                                ? "bg-blue-50 ml-12"
                                                : "bg-gray-100 mr-12"
                                                }`}
                                        >
                                            <Text type="tertiary" size="small" className="block mb-1">
                                                {msg.sender === "user" || msg.type === "user" ? "👤 Bạn" : "🤖 AI"}
                                                <span className="ml-2">{formatTime(msg.created_at || msg.timestamp)}</span>
                                                {msg.device_id ? (
                                                    <Tag size="small" color="blue" className="ml-2">
                                                        Device: {msg.device_id}
                                                    </Tag>
                                                ) : (
                                                    <span className="ml-2">—</span>
                                                )}
                                            </Text>
                                            <Text>{msg.content || msg.text || msg.message}</Text>
                                            {msg.audio_path && (
                                                <MessageAudio agentId={agentId} messageId={msg.id} />
                                            )}
                                        </div>
                                    ))}

                                    {/* Load More */}
                                    {messagesData?.total_pages && messagePage < messagesData.total_pages && (
                                        <div className="text-center py-2">
                                            <Button
                                                theme="borderless"
                                                onClick={loadMoreMessages}
                                                loading={isLoadingMessages}
                                            >
                                                {t("load_more", "Tải thêm")}
                                            </Button>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <Text type="tertiary" className="text-center block py-8">
                                    {t("no_messages", "Không có tin nhắn")}
                                </Text>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex items-center justify-center text-center">
                        <div>
                            <MessageSquare className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                            <Text type="tertiary">
                                {t("select_session", "Chọn một phiên để xem tin nhắn")}
                            </Text>
                        </div>
                    </div>
                )}
            </div>

            {/* Delete Confirmation */}
            <Modal
                title={
                    sessionToDelete === "ALL"
                        ? t("delete_all_confirm", "Xóa tất cả lịch sử?")
                        : t("delete_session_confirm", "Xóa phiên chat?")
                }
                visible={deleteModalOpen}
                onCancel={() => setDeleteModalOpen(false)}
                footer={
                    <div className="flex justify-end gap-2">
                        <Button onClick={() => setDeleteModalOpen(false)}>
                            {t("common:cancel", "Hủy")}
                        </Button>
                        <Button
                            type="danger"
                            theme="solid"
                            onClick={handleConfirmDelete}
                            loading={isDeleting}
                        >
                            {t("delete", "Xóa")}
                        </Button>
                    </div>
                }
            >
                <Text>
                    {sessionToDelete === "ALL"
                        ? t("delete_all_warning", "Tất cả lịch sử sẽ bị xóa vĩnh viễn.")
                        : t("delete_session_warning", "Phiên chat này sẽ bị xóa vĩnh viễn.")}
                </Text>
            </Modal>
        </div>
    );
}
