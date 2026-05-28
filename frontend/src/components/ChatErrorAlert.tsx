/**
 * ChatErrorAlert - Semi Design implementation
 */

import { useState, useEffect } from "react";
import { Modal, Typography, Button, Banner } from "@douyinfe/semi-ui";
import { IconAlertCircle } from "@douyinfe/semi-icons";
import type { ChatServiceError } from "@/types/chat";

const { Text, Title } = Typography;

type ChatErrorAlertProps = {
  error?: ChatServiceError | null;
  onDismiss: () => void;
};

export function ChatErrorAlert(props: ChatErrorAlertProps) {
  const { error, onDismiss } = props;
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (error) {
      setOpen(true);
    }
  }, [error]);

  const handleDismiss = () => {
    setOpen(false);
    onDismiss();
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-red-600">
          <IconAlertCircle />
          <Title heading={5} className="!mb-0">Lỗi</Title>
        </div>
      }
      visible={open}
      onCancel={handleDismiss}
      centered
      width={400}
      footer={
        <Button theme="solid" type="primary" block onClick={handleDismiss}>
          Đóng
        </Button>
      }
    >
      <div className="space-y-3">
        <Banner
          type="danger"
          description={error?.message || "Đã xảy ra lỗi không xác định"}
          fullMode={false}
        />
        {error?.code && (
          <Text type="tertiary" size="small" className="block">
            Code: {error.code}
          </Text>
        )}
      </div>
    </Modal>
  );
}

export default ChatErrorAlert;
