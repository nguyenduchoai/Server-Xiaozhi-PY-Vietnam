/**
 * ListReminders - Semi Design implementation
 * Display list of reminders with expand/collapse and actions
 */

import { useState, memo } from "react";
import { Clock, ChevronDown, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  Tag,
  Button,
  Dropdown,
  Typography,
  Empty,
  Card,
} from "@douyinfe/semi-ui";
import { IconMore, IconEdit, IconDelete, IconClock } from "@douyinfe/semi-icons";
import type { ReminderRead, ReminderStatus } from "@types";

const { Text, Paragraph } = Typography;

interface ListRemindersProps {
  reminders: ReminderRead[];
  onEdit?: (reminder: ReminderRead) => void;
  onDelete?: (reminderId: string) => void;
}

const statusColorMap: Record<ReminderStatus, "blue" | "green" | "red" | "grey"> = {
  pending: "grey",
  delivered: "blue",
  received: "green",
  failed: "red",
};

const statusLabelMap: Record<ReminderStatus, string> = {
  pending: "Đang chờ",
  delivered: "Đã gửi",
  received: "Đã nhận",
  failed: "Thất bại",
};

const formatDateTime = (value: string) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const ListRemindersComponent = ({
  reminders,
  onEdit,
  onDelete,
}: ListRemindersProps) => {
  const { t } = useTranslation("agents");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    const next = new Set(expanded);
    next.has(id) ? next.delete(id) : next.add(id);
    setExpanded(next);
  };

  if (!reminders || reminders.length === 0) {
    return (
      <Card className="!border-dashed" bodyStyle={{ padding: 24 }}>
        <Empty
          image={<IconClock className="text-gray-300" style={{ fontSize: 48 }} />}
          title={t("no_reminders", "No reminders yet")}
        />
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {reminders.map((reminder) => {
        const isOpen = expanded.has(reminder.id);
        const tagColor = statusColorMap[reminder.status];
        const statusLabel = statusLabelMap[reminder.status] ?? reminder.status;

        return (
          <Card key={reminder.id} bodyStyle={{ padding: 0 }}>
            <div
              className="px-4 py-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              onClick={() => toggle(reminder.id)}
            >
              <div className="flex items-start gap-3">
                <div className="mt-1">
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  )}
                </div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <Text strong className="text-sm">
                      {reminder.title || t("reminder", "Reminder")}
                    </Text>
                    <Tag size="small" color={tagColor}>{statusLabel}</Tag>
                  </div>
                  <Paragraph
                    type="tertiary"
                    className="text-sm !mb-1"
                    ellipsis={{ rows: 2 }}
                  >
                    {reminder.content}
                  </Paragraph>
                  <div className="flex items-center gap-2 text-xs">
                    <Clock className="h-3.5 w-3.5 text-gray-400" />
                    <Text type="tertiary" size="small">
                      {formatDateTime(reminder.remind_at_local || reminder.remind_at)}
                    </Text>
                  </div>
                </div>
                <Dropdown
                  trigger="click"
                  position="bottomRight"
                  clickToHide
                  render={
                    <Dropdown.Menu>
                      <Dropdown.Item onClick={() => onEdit?.(reminder)}>
                        <IconEdit className="mr-2" />
                        {t("edit", "Edit")}
                      </Dropdown.Item>
                      <Dropdown.Item type="danger" onClick={() => onDelete?.(reminder.id)}>
                        <IconDelete className="mr-2" />
                        {t("delete", "Delete")}
                      </Dropdown.Item>
                    </Dropdown.Menu>
                  }
                >
                  <Button
                    icon={<IconMore />}
                    theme="borderless"
                    type="tertiary"
                    size="small"
                    onClick={(e) => e.stopPropagation()}
                  />
                </Dropdown>
              </div>
            </div>

            {isOpen && (
              <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-800 pt-3 ml-7">
                <div className="space-y-3">
                  <div>
                    <Text strong size="small" className="block mb-1">
                      {t("content", "Content")}:
                    </Text>
                    <Paragraph className="whitespace-pre-wrap text-sm">
                      {reminder.content}
                    </Paragraph>
                  </div>
                  {reminder.reminder_metadata && (
                    <div>
                      <Text strong size="small" className="block mb-1">
                        Metadata:
                      </Text>
                      <pre className="rounded-lg bg-gray-100 dark:bg-gray-800 p-3 text-xs overflow-auto">
                        {JSON.stringify(reminder.reminder_metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
};

export const ListReminders = memo(ListRemindersComponent);
