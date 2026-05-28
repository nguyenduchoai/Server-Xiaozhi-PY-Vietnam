/**
 * SessionMessages - Semi Design implementation
 * Chat message history with scroll pagination
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Skeleton, Spin, Tag, Typography } from "@douyinfe/semi-ui";
import type { AgentMessage } from "@types";
import apiClient from "@config/axios-instance";
import { AGENT_ENDPOINTS } from "@api";

const { Text } = Typography;

const formatTime = (dateString: string) => {
  return new Date(dateString).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
};

interface SessionMessagesProps {
  agentId: string;
  sessionId: string;
  onLoadMore: (page: number) => void;
  hasMore: boolean;
  isLoading: boolean;
  messages: AgentMessage[];
}

export function SessionMessages({
  agentId,
  sessionId,
  onLoadMore,
  hasMore,
  isLoading,
  messages,
}: SessionMessagesProps) {
  const { t } = useTranslation("agents");
  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const [messagePage, setMessagePage] = useState(1);
  const isLoadingMoreRef = useRef(false);

  useEffect(() => {
    setMessagePage(1);
  }, [sessionId]);

  const previousMessagesLengthRef = useRef(messages.length);
  const scrollPositionRef = useRef<number | null>(null);

  useEffect(() => {
    if (messages.length > 0 && scrollViewportRef.current) {
      if (messagePage === 1) {
        scrollViewportRef.current.scrollTop = scrollViewportRef.current.scrollHeight;
      } else if (previousMessagesLengthRef.current < messages.length) {
        if (scrollPositionRef.current !== null && scrollViewportRef.current) {
          const newScrollHeight = scrollViewportRef.current.scrollHeight;
          const scrollDiff = newScrollHeight - scrollPositionRef.current;
          scrollViewportRef.current.scrollTop = scrollDiff;
          scrollPositionRef.current = null;
        }
      }
      previousMessagesLengthRef.current = messages.length;
    }
  }, [messages.length, messagePage]);

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const target = e.currentTarget;
      const scrollTop = target.scrollTop;

      if (scrollTop < 50 && hasMore && !isLoading && !isLoadingMoreRef.current) {
        isLoadingMoreRef.current = true;
        const nextPage = messagePage + 1;
        setMessagePage(nextPage);
        scrollPositionRef.current = target.scrollHeight;
        onLoadMore(nextPage);

        setTimeout(() => {
          isLoadingMoreRef.current = false;
        }, 500);
      }
    },
    [hasMore, isLoading, messagePage, onLoadMore]
  );

  const reversedMessages = [...messages].reverse();

  return (
    <div className="h-full w-full overflow-hidden">
      <div
        ref={scrollViewportRef}
        className="h-full overflow-y-auto"
        onScroll={handleScroll}
      >
        <div className="flex flex-col space-y-4 p-6">
          {/* Loading indicator at top */}
          {isLoading && messagePage > 1 && (
            <div className="flex justify-center py-4">
              <Spin size="small" />
            </div>
          )}

          {/* No more messages indicator */}
          {!hasMore && messages.length > 0 && (
            <div className="flex justify-center py-2">
              <Text type="tertiary" size="small">
                {t("no_more_messages", "No more messages")}
              </Text>
            </div>
          )}

          {/* Loading skeleton */}
          {isLoading && messagePage === 1 ? (
            <>
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className={`flex w-full ${i % 2 === 0 ? "justify-end" : "justify-start"}`}
                >
                  <Skeleton.Paragraph rows={2} style={{ width: "60%" }} />
                </div>
              ))}
            </>
          ) : (
            <>
              {reversedMessages.map((msg) => (
                <MessageItem key={msg.id} message={msg} agentId={agentId} />
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const MessageItem = ({
  message,
  agentId,
}: {
  message: AgentMessage;
  agentId: string;
}) => {
  const isUser = message.chat_type === 1;
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioLoading, setAudioLoading] = useState(false);

  // Load audio blob on demand (axios sends the Bearer token)
  const handleLoadAudio = useCallback(async () => {
    if (audioUrl || audioLoading) return;
    setAudioLoading(true);
    try {
      const { data } = await apiClient.get<Blob>(
        AGENT_ENDPOINTS.MESSAGE_AUDIO(agentId, message.id),
        { responseType: "blob" }
      );
      setAudioUrl(URL.createObjectURL(data));
    } catch {
      setAudioUrl(null);
    } finally {
      setAudioLoading(false);
    }
  }, [agentId, message.id, audioUrl, audioLoading]);

  // Revoke object URL on unmount to avoid leaks
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 text-sm ${isUser
            ? "bg-blue-500 text-white rounded-br-none"
            : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-none"
          }`}
      >
        <div className="whitespace-pre-wrap break-words">{message.content}</div>

        {/* Voice replay (only when audio was saved, chat_history_conf=2) */}
        {message.audio_path &&
          (audioUrl ? (
            <audio
              controls
              src={audioUrl}
              className="mt-2 h-8 w-full"
            />
          ) : (
            <button
              type="button"
              onClick={handleLoadAudio}
              disabled={audioLoading}
              className={`mt-2 inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] ${isUser
                  ? "bg-white/20 text-white hover:bg-white/30"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-300"
                }`}
            >
              {audioLoading ? "..." : "▶ Voice"}
            </button>
          ))}

        <div
          className={`mt-1 flex items-center gap-2 text-[10px] opacity-70 ${isUser ? "text-white/80" : "text-gray-500"
            }`}
        >
          <span>{formatTime(message.created_at)}</span>
          {message.device_id ? (
            <Tag size="small" color={isUser ? "grey" : "blue"}>
              Device: {message.device_id}
            </Tag>
          ) : (
            <span>—</span>
          )}
        </div>
      </div>
    </div>
  );
};
