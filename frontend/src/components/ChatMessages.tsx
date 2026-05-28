
"use client";

import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import Markdown from "react-markdown";
import type { ChatMessage } from "@/types/chat";
import { Empty } from "@douyinfe/semi-ui";
import { IconComment } from "@douyinfe/semi-icons";

type ChatMessagesProps = {
  messages: ChatMessage[];
  isConnected: boolean;
};

const markdownComponents = {
  p: ({ children }: { children?: ReactNode }) => (
    <p style={{ marginBottom: 4 }}>{children}</p>
  ),
  code: ({ children }: { children?: ReactNode }) => (
    <code style={{ fontSize: '0.875em', backgroundColor: 'rgba(0,0,0,0.1)', padding: '2px 4px', borderRadius: 4 }}>
      {children}
    </code>
  ),
  pre: ({ children }: { children?: ReactNode }) => (
    <pre style={{ padding: 8, borderRadius: 4, backgroundColor: 'rgba(0,0,0,0.1)', overflowX: 'auto', marginBottom: 4 }}>
      {children}
    </pre>
  ),
  a: ({ children, href }: { children?: ReactNode; href?: string }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={{ textDecoration: 'underline', color: 'var(--semi-color-link)' }}
    >
      {children}
    </a>
  ),
  img: ({ src, alt }: { src?: string; alt?: string }) => (
    <a href={src} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-block', margin: '6px 0' }}>
      <img
        src={src}
        alt={alt || ''}
        style={{
          maxWidth: '100%',
          maxHeight: 240,
          borderRadius: 8,
          border: '1px solid var(--semi-color-border)',
          cursor: 'pointer',
          objectFit: 'cover',
        }}
        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
      />
    </a>
  ),
} as const;

export function ChatMessages(props: ChatMessagesProps) {
  const { t } = useTranslation("chat");
  const { messages, isConnected } = props;

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <Empty
          image={<IconComment style={{ fontSize: 48, color: 'var(--semi-color-text-2)' }} />}
          title={t("no_messages")}
          description={isConnected ? t("start_conversation") : t("connect_to_server_first")}
        />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {messages.map((msg, idx) => (
        <div
          key={idx}
          className={`flex ${msg.type === "user" || msg.type === "stt"
            ? "justify-end"
            : "justify-start"
            }`}
        >
          <div
            style={{
              maxWidth: '75%',
              borderRadius: 12,
              padding: '8px 16px',
              backgroundColor: msg.type === "user" || msg.type === "stt"
                ? 'var(--semi-color-primary)'
                : msg.type === "tts"
                  ? 'var(--semi-color-tertiary)'
                  : 'var(--semi-color-bg-1)',
              color: msg.type === "user" || msg.type === "stt"
                ? 'white'
                : msg.type === "tts"
                  ? 'var(--semi-color-text-0)'
                  : 'var(--semi-color-text-0)',
              border: msg.type !== "user" && msg.type !== "stt" ? '1px solid var(--semi-color-border)' : 'none',
              boxShadow: 'var(--semi-shadow-elevated)'
            }}
          >
            {(msg.type === "stt" || msg.type === "tts") && (
              <div style={{ opacity: 0.75, fontSize: 12, marginBottom: 4 }}>
                {msg.type === "stt" && "🎤 Recognized:"}
                {msg.type === "tts" && "🔊 Playing:"}
              </div>
            )}
            <div style={{ wordBreak: 'break-word', fontSize: 14 }}>
              <Markdown components={markdownComponents}>{msg.text}</Markdown>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
