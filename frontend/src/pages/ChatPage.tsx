
"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useDeviceList } from "@/hooks";
import { useChatWebSocket } from "@/hooks/use-chat-websocket";
import type { ChatServiceConfig } from "@/types/chat";
import type { Device } from "@/types";
import { ChatHeader } from "@/components/ChatHeader";
import { ChatErrorAlert } from "@/components/ChatErrorAlert";
import { ActivationDialog } from "@/components/ActivationDialog";
import { ChatInputArea } from "@/components/ChatInputArea";
import { ChatMessages } from "@/components/ChatMessages";
import { PageHead } from "@/components/PageHead";
import { Layout } from "@douyinfe/semi-ui";

const { Header, Content, Footer } = Layout;

/**
 * Generate a random UUID v4 for clientId
 */
function generateRandomClientId(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const ChatPage = () => {
  const { user } = useAuth();

  // Fetch devices once on mount
  const {
    data: deviceListData,
    isLoading: isLoadingDevices,
    error: deviceError,
  } = useDeviceList({
    page: 1,
    page_size: 100, // Fetch up to 100 devices
  });

  const devices = useMemo(() => deviceListData?.data || [], [deviceListData]);
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const clientIdRef = useRef<string>(generateRandomClientId());

  // Initialize chat service
  const {
    isConnected,
    isConnecting,
    isRecording,
    messages,
    error,
    activation,
    connect,
    disconnect,
    sendMessage,
    startRecording,
    stopRecording,
    clearError,
    clearActivation,
  } = useChatWebSocket({
    config: {
      deviceId: selectedDevice?.mac_address || "web_test_client",
      deviceMac: selectedDevice?.mac_address || "00:11:22:33:44:55",
      deviceName: selectedDevice?.device_name || "Web Chat Client",
      clientId: clientIdRef.current,
      token: user?.id || "test-token",
      otaUrl: import.meta.env.VITE_OTA_URL,
    } as ChatServiceConfig,
  });

  // Auto-scroll handled below when messages change

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!messagesEndRef.current) {
      return;
    }
    messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = (message: string) => {
    sendMessage(message);
  };

  const handleToggleRecording = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      try {
        await startRecording();
      } catch (err) {
        console.error("Failed to start recording:", err);
      }
    }
  };

  return (
    <>
      <PageHead
        title="chat:page.title"
        description="chat:page.description"
        translateTitle
        translateDescription
      />
      <Layout style={{ height: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Header>
          <ChatHeader
            userName={user?.name}
            isConnected={isConnected}
            isConnecting={isConnecting}
            onConnect={connect}
            onDisconnect={disconnect}
            selectedDevice={selectedDevice}
            devices={devices}
            isLoadingDevices={isLoadingDevices}
            deviceError={deviceError}
            onSelectDevice={setSelectedDevice}
          />
        </Header>

        {/* Error Alert */}
        <ChatErrorAlert error={error} onDismiss={clearError} />

        {/* Activation Dialog */}
        <ActivationDialog activation={activation} onDismiss={clearActivation} />

        {/* Messages Container */}
        <Content style={{ flex: 1, overflow: 'auto', padding: 12, backgroundColor: 'var(--semi-color-bg-2)' }}>
          <ChatMessages messages={messages} isConnected={isConnected} />
          <div ref={messagesEndRef} aria-hidden />
        </Content>

        {/* Input Area */}
        <Footer style={{ padding: 16, borderTop: '1px solid var(--semi-color-border)', backgroundColor: 'var(--semi-color-bg-1)' }}>
          <div style={{ maxWidth: 800, margin: '0 auto' }}>
            <ChatInputArea
              isConnected={isConnected}
              isRecording={isRecording}
              onSendMessage={handleSendMessage}
              onToggleRecording={handleToggleRecording}
            />
          </div>
        </Footer>
      </Layout>
    </>
  );
}

export default ChatPage;
