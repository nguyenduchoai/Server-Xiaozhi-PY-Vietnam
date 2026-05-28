
"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { IconSend } from "@douyinfe/semi-icons";
import { Button, TextArea } from "@douyinfe/semi-ui";
import { RecordingTimer } from "@/components/RecordingTimer";

type ChatInputAreaProps = {
  isConnected: boolean;
  isRecording: boolean;
  onSendMessage: (message: string) => void;
  onToggleRecording: () => void;
};

export function ChatInputArea(props: ChatInputAreaProps) {
  const { t } = useTranslation("chat");
  const [messageInput, setMessageInput] = useState("");

  const handleSendMessage = () => {
    if (messageInput.trim() && props.isConnected) {
      props.onSendMessage(messageInput);
      setMessageInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex items-end gap-3">
      <TextArea
        value={messageInput}
        onChange={(val) => setMessageInput(val)}
        onKeyDown={handleKeyDown}
        placeholder={
          props.isConnected
            ? t("message_placeholder_connected")
            : t("message_placeholder_disconnected")
        }
        disabled={!props.isConnected || props.isRecording}
        rows={2}
        autosize={{ minRows: 2, maxRows: 6 }}
        style={{ flex: 1 }}
      />
      <div className="flex flex-col gap-2">
        <Button
          onClick={handleSendMessage}
          disabled={
            !props.isConnected || !messageInput.trim() || props.isRecording
          }
          theme="solid"
          type="primary"
          icon={<IconSend />}
          style={{ width: '100%' }}
        />
        <RecordingTimer
          isRecording={props.isRecording}
          isConnected={props.isConnected}
          onToggleRecording={props.onToggleRecording}
        />
      </div>
    </div>
  );
}
