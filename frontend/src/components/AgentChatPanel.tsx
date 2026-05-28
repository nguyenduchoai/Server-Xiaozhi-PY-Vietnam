/**
 * AgentChatPanel — Browser-based chat for testing an agent
 * Embedded in Agent Detail page as a tab.
 * 
 * Features:
 * - Text input → sends to agent's LLM
 * - Rich response with Markdown (images, links)
 * - Conversation history within session
 * - Clear session button
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Button, Input, Spin, Toast, Empty, Typography } from '@douyinfe/semi-ui';
import { IconSend } from '@douyinfe/semi-icons';
import { MessageCircle, Bot, User, Trash2 } from 'lucide-react';
import Markdown from 'react-markdown';
import axiosInstance from '@/config/axios-instance';

const { Text } = Typography;

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
    images?: string[];
}

interface AgentChatPanelProps {
    agentId: string;
    agentName?: string;
}

const markdownComponents = {
    p: ({ children }: { children?: React.ReactNode }) => (
        <p style={{ margin: '4px 0', lineHeight: 1.6 }}>{children}</p>
    ),
    a: ({ children, href }: { children?: React.ReactNode; href?: string }) => (
        <a href={href} target="_blank" rel="noopener noreferrer"
            style={{ color: 'var(--semi-color-link)', textDecoration: 'underline' }}>
            {children}
        </a>
    ),
    img: ({ src, alt }: { src?: string; alt?: string }) => (
        <a href={src} target="_blank" rel="noopener noreferrer"
            style={{ display: 'inline-block', margin: '8px 0' }}>
            <img src={src} alt={alt || ''}
                style={{
                    maxWidth: '100%', maxHeight: 280, borderRadius: 12,
                    border: '1px solid var(--semi-color-border)',
                    cursor: 'pointer', objectFit: 'cover',
                }}
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
        </a>
    ),
    code: ({ children }: { children?: React.ReactNode }) => (
        <code style={{
            fontSize: '0.85em', backgroundColor: 'rgba(0,0,0,0.06)',
            padding: '2px 6px', borderRadius: 4
        }}>{children}</code>
    ),
    pre: ({ children }: { children?: React.ReactNode }) => (
        <pre style={{
            padding: 12, borderRadius: 8, backgroundColor: 'rgba(0,0,0,0.06)',
            overflowX: 'auto', marginBottom: 8, fontSize: '0.85em'
        }}>{children}</pre>
    ),
    strong: ({ children }: { children?: React.ReactNode }) => (
        <strong style={{ fontWeight: 600 }}>{children}</strong>
    ),
    ul: ({ children }: { children?: React.ReactNode }) => (
        <ul style={{ paddingLeft: 20, margin: '4px 0' }}>{children}</ul>
    ),
    ol: ({ children }: { children?: React.ReactNode }) => (
        <ol style={{ paddingLeft: 20, margin: '4px 0' }}>{children}</ol>
    ),
} as const;

// ── LocalStorage helpers ──
const STORAGE_KEY_PREFIX = 'agent_chat_';

function loadChatState(agentId: string): { messages: ChatMessage[]; sessionId: string | null } {
    try {
        const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${agentId}`);
        if (raw) {
            const data = JSON.parse(raw);
            return {
                messages: data.messages || [],
                sessionId: data.sessionId || null,
            };
        }
    } catch { /* ignore */ }
    return { messages: [], sessionId: null };
}

function saveChatState(agentId: string, messages: ChatMessage[], sessionId: string | null) {
    try {
        // Keep max 100 messages in localStorage
        const trimmed = messages.slice(-100);
        localStorage.setItem(`${STORAGE_KEY_PREFIX}${agentId}`, JSON.stringify({
            messages: trimmed,
            sessionId,
            updatedAt: Date.now(),
        }));
    } catch { /* localStorage full, ignore */ }
}

function clearChatState(agentId: string) {
    try {
        localStorage.removeItem(`${STORAGE_KEY_PREFIX}${agentId}`);
    } catch { /* ignore */ }
}

export default function AgentChatPanel({ agentId, agentName }: AgentChatPanelProps) {
    // Initialize from localStorage (single load)
    const [initialState] = useState(() => loadChatState(agentId));
    const [messages, setMessages] = useState<ChatMessage[]>(initialState.messages);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(initialState.sessionId);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Save to localStorage whenever messages or sessionId change
    useEffect(() => {
        saveChatState(agentId, messages, sessionId);
    }, [agentId, messages, sessionId]);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Focus input on mount
    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const sendMessage = useCallback(async () => {
        const text = input.trim();
        if (!text || loading) return;

        // Add user message
        const userMsg: ChatMessage = {
            role: 'user', content: text, timestamp: Date.now(),
        };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await axiosInstance.post(`/agents/${agentId}/chat`, {
                message: text,
                session_id: sessionId,
            });

            const { reply, session_id, images } = res.data;
            setSessionId(session_id);

            const botMsg: ChatMessage = {
                role: 'assistant', content: reply, timestamp: Date.now(), images,
            };
            setMessages(prev => [...prev, botMsg]);

        } catch (err: any) {
            const errMsg = err?.response?.data?.detail || 'Lỗi kết nối';
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `⚠️ ${errMsg}`,
                timestamp: Date.now(),
            }]);
            Toast.error(errMsg);
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
    }, [input, loading, agentId, sessionId]);

    const clearSession = useCallback(async () => {
        if (sessionId) {
            try {
                await axiosInstance.delete(`/agents/${agentId}/chat/${sessionId}`);
            } catch { /* ignore */ }
        }
        setMessages([]);
        setSessionId(null);
        clearChatState(agentId);
        Toast.info('Đã xóa hội thoại');
    }, [agentId, sessionId]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div style={{
            display: 'flex', flexDirection: 'column',
            height: 'calc(100vh - 260px)', minHeight: 400,
            border: '1px solid var(--semi-color-border)',
            borderRadius: 12, overflow: 'hidden',
            backgroundColor: 'var(--semi-color-bg-1)',
        }}>
            {/* Header */}
            <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid var(--semi-color-border)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                backgroundColor: 'var(--semi-color-bg-2)',
            }}>
                <div className="flex items-center gap-2">
                    <MessageCircle size={18} />
                    <Text strong>Chat với {agentName || 'Agent'}</Text>
                    {sessionId && (
                        <Text type="tertiary" size="small">• {messages.length} tin nhắn</Text>
                    )}
                </div>
                {messages.length > 0 && (
                    <Button
                        icon={<Trash2 size={14} />}
                        size="small"
                        theme="borderless"
                        type="tertiary"
                        onClick={clearSession}
                    >
                        Xóa
                    </Button>
                )}
            </div>

            {/* Messages */}
            <div style={{
                flex: 1, overflowY: 'auto', padding: 16,
                backgroundColor: 'var(--semi-color-bg-2)',
            }}>
                {messages.length === 0 ? (
                    <div className="flex h-full items-center justify-center">
                        <Empty
                            image={<Bot size={48} style={{ color: 'var(--semi-color-text-2)' }} />}
                            title="Bắt đầu trò chuyện"
                            description="Nhập tin nhắn để test agent. Hỗ trợ hiển thị hình ảnh, link, markdown."
                        />
                    </div>
                ) : (
                    <div className="space-y-4">
                        {messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                            >
                                {/* Avatar */}
                                <div className="shrink-0 mt-1">
                                    {msg.role === 'user' ? (
                                        <div style={{
                                            width: 32, height: 32, borderRadius: '50%',
                                            backgroundColor: 'var(--semi-color-primary)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        }}>
                                            <User size={16} style={{ color: 'white' }} />
                                        </div>
                                    ) : (
                                        <div style={{
                                            width: 32, height: 32, borderRadius: '50%',
                                            backgroundColor: 'var(--semi-color-success)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        }}>
                                            <Bot size={16} style={{ color: 'white' }} />
                                        </div>
                                    )}
                                </div>

                                {/* Message Bubble */}
                                <div style={{
                                    maxWidth: '80%',
                                    padding: '10px 16px',
                                    borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                                    backgroundColor: msg.role === 'user'
                                        ? 'var(--semi-color-primary)'
                                        : 'var(--semi-color-bg-1)',
                                    color: msg.role === 'user' ? 'white' : 'var(--semi-color-text-0)',
                                    border: msg.role === 'user' ? 'none' : '1px solid var(--semi-color-border)',
                                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                                    wordBreak: 'break-word',
                                    fontSize: 14,
                                    lineHeight: 1.6,
                                }}>
                                    {msg.role === 'user' ? (
                                        <span>{msg.content}</span>
                                    ) : (
                                        <Markdown components={markdownComponents}>{msg.content}</Markdown>
                                    )}
                                </div>
                            </div>
                        ))}

                        {/* Loading indicator */}
                        {loading && (
                            <div className="flex gap-3">
                                <div className="shrink-0 mt-1">
                                    <div style={{
                                        width: 32, height: 32, borderRadius: '50%',
                                        backgroundColor: 'var(--semi-color-success)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    }}>
                                        <Bot size={16} style={{ color: 'white' }} />
                                    </div>
                                </div>
                                <div style={{
                                    padding: '12px 20px', borderRadius: '16px 16px 16px 4px',
                                    backgroundColor: 'var(--semi-color-bg-1)',
                                    border: '1px solid var(--semi-color-border)',
                                }}>
                                    <Spin size="small" />
                                    <Text type="tertiary" size="small" style={{ marginLeft: 8 }}>
                                        Đang suy nghĩ...
                                    </Text>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div style={{
                padding: '12px 16px',
                borderTop: '1px solid var(--semi-color-border)',
                backgroundColor: 'var(--semi-color-bg-1)',
            }}>
                <div className="flex gap-2">
                    <Input
                        ref={inputRef as any}
                        value={input}
                        onChange={setInput}
                        onKeyDown={handleKeyDown}
                        placeholder="Nhập tin nhắn... (Enter để gửi)"
                        size="large"
                        disabled={loading}
                        style={{ flex: 1 }}
                    />
                    <Button
                        icon={<IconSend />}
                        theme="solid"
                        type="primary"
                        size="large"
                        loading={loading}
                        disabled={!input.trim()}
                        onClick={sendMessage}
                    >
                        Gửi
                    </Button>
                </div>
                <div style={{ marginTop: 6 }}>
                    <Text type="quaternary" size="small">
                        💡 Thử hỏi: "Có sản phẩm nào không?", "Giới thiệu sản phẩm đi", "Cái nào rẻ nhất?"
                    </Text>
                </div>
            </div>
        </div>
    );
}
