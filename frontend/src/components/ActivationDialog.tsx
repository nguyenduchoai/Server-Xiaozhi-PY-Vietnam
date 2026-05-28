/**
 * ActivationDialog - Semi Design implementation
 * Shows device activation code with countdown timer
 */

import { useEffect, useState } from "react";
import { Modal, Typography, Button } from "@douyinfe/semi-ui";
import type { ActivationData } from "@/types/chat";

const { Text, Title } = Typography;

type ActivationDialogProps = {
  activation?: ActivationData | null;
  onDismiss: () => void;
};

export function ActivationDialog(props: ActivationDialogProps) {
  const { activation, onDismiss } = props;
  const [open, setOpen] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);

  useEffect(() => {
    if (activation) {
      setOpen(true);
      setTimeLeft(activation.timeout_ms / 1000);
    }
  }, [activation]);

  // Countdown timer
  useEffect(() => {
    if (!open || timeLeft <= 0) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        const newTime = prev - 1;
        if (newTime <= 0) {
          setOpen(false);
          onDismiss();
          return 0;
        }
        return newTime;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [open, timeLeft, onDismiss]);

  const handleDismiss = () => {
    setOpen(false);
    onDismiss();
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <span className="text-2xl">🔐</span>
          <Title heading={4} className="!mb-0">Mã Kích Hoạt</Title>
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
      <div className="space-y-4 py-2">
        <Text type="tertiary" className="block text-center">
          {activation?.message}
        </Text>

        {/* Code Display */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl p-6 text-center">
          <Text type="tertiary" size="small" className="block mb-2">
            Nhập mã này trong ứng dụng
          </Text>
          <div className="text-4xl font-bold tracking-[0.5em] text-blue-600 dark:text-blue-400 font-mono">
            {activation?.code}
          </div>
        </div>

        {/* Countdown */}
        <div className="text-center">
          <Text type="tertiary" size="small">
            Hết hạn sau{" "}
            <span className={`font-bold ${timeLeft < 30 ? 'text-red-500' : 'text-blue-500'}`}>
              {Math.max(0, timeLeft)}s
            </span>
          </Text>

          {/* Progress bar */}
          <div className="mt-2 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-1000 ease-linear"
              style={{ width: `${(timeLeft / (activation?.timeout_ms ? activation.timeout_ms / 1000 : 300)) * 100}%` }}
            />
          </div>
        </div>
      </div>
    </Modal>
  );
}

export default ActivationDialog;
