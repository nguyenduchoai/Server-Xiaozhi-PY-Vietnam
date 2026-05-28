/**
 * ReminderDialog - Semi Design implementation
 * Create and edit reminders with timezone-aware datetime
 */

import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Bell } from "lucide-react";
import {
  Modal,
  Typography,
  Input,
  TextArea,
  Button,
  DatePicker,
  Banner,
} from "@douyinfe/semi-ui";
import { IconClock, IconAlarm } from "@douyinfe/semi-icons";
import type {
  CreateReminderPayload,
  ReminderRead,
  UpdateReminderPayload,
} from "@types";

const { Text, Title } = Typography;

interface ReminderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reminder?: ReminderRead | null;
  onSubmit: (
    payload: CreateReminderPayload | UpdateReminderPayload
  ) => void | Promise<void>;
  isLoading?: boolean;
}

const toInitialMetadata = (metadata?: Record<string, unknown> | null) => {
  if (!metadata) return "";
  try {
    return JSON.stringify(metadata, null, 2);
  } catch {
    return "";
  }
};

export const ReminderDialog = ({
  open,
  onOpenChange,
  reminder,
  onSubmit,
  isLoading = false,
}: ReminderDialogProps) => {
  const { t } = useTranslation("agents");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [remindAt, setRemindAt] = useState<Date | undefined>(undefined);
  const [metadata, setMetadata] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isEditMode = !!reminder;
  const modeLabel = useMemo(
    () =>
      reminder
        ? t("update_reminder", "Cập nhật nhắc nhở")
        : t("create_reminder", "Tạo nhắc nhở"),
    [reminder, t]
  );

  useEffect(() => {
    if (open) {
      setTitle(reminder?.title ?? "");
      setContent(reminder?.content ?? "");
      setRemindAt(reminder?.remind_at_local ? new Date(reminder.remind_at_local) : undefined);
      setMetadata(toInitialMetadata(reminder?.reminder_metadata));
      setError(null);
    }
  }, [reminder, open]);

  const toOffsetDateTime = (date: Date) => {
    if (!date || isNaN(date.getTime())) return "";
    const pad = (num: number) => String(num).padStart(2, "0");
    const year = date.getFullYear();
    const month = pad(date.getMonth() + 1);
    const day = pad(date.getDate());
    const hours = pad(date.getHours());
    const minutes = pad(date.getMinutes());
    const seconds = pad(date.getSeconds());
    const tzMinutes = date.getTimezoneOffset();
    const sign = tzMinutes > 0 ? "-" : "+";
    const abs = Math.abs(tzMinutes);
    const offset = `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}${offset}`;
  };

  const handleSubmit = async () => {
    setError(null);

    if (!content.trim()) {
      setError(t("content_required", "Vui lòng nhập nội dung"));
      return;
    }

    if (!remindAt) {
      setError(t("time_required", "Vui lòng chọn thời gian"));
      return;
    }

    let parsedMetadata: Record<string, unknown> | undefined;
    if (metadata.trim()) {
      try {
        parsedMetadata = JSON.parse(metadata);
      } catch (err) {
        setError(t("invalid_metadata", "Metadata JSON không hợp lệ"));
        return;
      }
    }

    const payload: CreateReminderPayload | UpdateReminderPayload = {
      title: title || undefined,
      content,
      remind_at: toOffsetDateTime(remindAt),
      reminder_metadata: parsedMetadata,
    };

    await onSubmit(payload);
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${isEditMode
            ? 'bg-gradient-to-br from-orange-500 to-red-500'
            : 'bg-gradient-to-br from-blue-500 to-purple-600'}`}
          >
            <Bell className="h-5 w-5 text-white" />
          </div>
          <div>
            <Title heading={5} className="!mb-0">{modeLabel}</Title>
            <Text type="tertiary" size="small">
              {t("reminder_dialog_desc", "Thiết lập nhắc nhở với múi giờ địa phương")}
            </Text>
          </div>
        </div>
      }
      visible={open}
      onCancel={() => onOpenChange(false)}
      width={480}
      footer={
        <div className="flex justify-end gap-3">
          <Button onClick={() => onOpenChange(false)}>
            {t("cancel", "Hủy")}
          </Button>
          <Button
            theme="solid"
            type="primary"
            onClick={handleSubmit}
            loading={isLoading}
            icon={<IconAlarm />}
          >
            {isLoading ? t("saving", "Đang lưu...") : t("save", "Lưu")}
          </Button>
        </div>
      }
      bodyStyle={{ padding: "16px 24px" }}
    >
      <div className="space-y-4">
        {/* Title */}
        <div>
          <Text strong className="text-sm mb-1.5 block">
            {t("title", "Tiêu đề")}
          </Text>
          <Input
            size="large"
            value={title}
            onChange={(v) => setTitle(v)}
            placeholder={t("reminder_title_placeholder", "Ví dụ: Nhắc đi ngủ")}
            prefix={<span>📝</span>}
          />
        </div>

        {/* Content */}
        <div>
          <Text strong className="text-sm mb-1.5 block">
            {t("content", "Nội dung")} <Text type="danger">*</Text>
          </Text>
          <TextArea
            value={content}
            onChange={(v) => setContent(v)}
            placeholder={t("reminder_content_placeholder", "Nội dung nhắc nhở...")}
            rows={3}
            autosize
          />
        </div>

        {/* DateTime Picker */}
        <div>
          <Text strong className="text-sm mb-1.5 block">
            {t("remind_at", "Thời gian")} <Text type="danger">*</Text>
          </Text>
          <DatePicker
            type="dateTime"
            value={remindAt}
            onChange={(date) => setRemindAt(date as Date)}
            style={{ width: "100%" }}
            format="dd/MM/yyyy HH:mm"
            placeholder={t("select_datetime", "Chọn ngày giờ")}
            prefix={<IconClock />}
          />
          <Text type="tertiary" size="small" className="mt-1 block">
            {t("remind_at_hint_local", "Thời gian theo giờ địa phương (UTC+7)")}
          </Text>
        </div>

        {/* Metadata (Optional) */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Text strong className="text-sm">Metadata (JSON)</Text>
            <Text type="tertiary" size="small">- Tùy chọn</Text>
          </div>
          <TextArea
            value={metadata}
            onChange={(v) => setMetadata(v)}
            placeholder={`{\n  "priority": "high"\n}`}
            rows={2}
            autosize
          />
        </div>

        {/* Error Message */}
        {error && (
          <Banner type="danger" description={error} closeIcon={null} />
        )}
      </div>
    </Modal>
  );
};

export default ReminderDialog;
