/**
 * KnowledgeEntryCard - Semi Design implementation
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Card, Tag, Button, Dropdown, Typography, Toast } from "@douyinfe/semi-ui";
import { IconMore, IconCopy, IconEdit, IconDelete, IconTick } from "@douyinfe/semi-icons";
import { KnowledgeSectorBadge } from "./KnowledgeSectorBadge";
import type { KnowledgeEntry } from "@/types";

const { Text, Paragraph } = Typography;

type KnowledgeEntryCardProps = {
  entry: KnowledgeEntry;
  onEdit?: (entry: KnowledgeEntry) => void;
  onDelete?: (entryId: string) => void;
  className?: string;
};

export const KnowledgeEntryCard = ({
  entry,
  onEdit,
  onDelete,
  className,
}: KnowledgeEntryCardProps) => {
  const { t, i18n } = useTranslation("agents");
  const [isCopied, setIsCopied] = useState(false);

  const truncatedContent =
    entry.content.length > 200
      ? `${entry.content.slice(0, 200)}...`
      : entry.content;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(entry.content);
    setIsCopied(true);
    Toast.success(t("copied"));
    setTimeout(() => setIsCopied(false), 2000);
  };

  const formatDate = (dateValue: string | number | undefined | null) => {
    if (!dateValue) return null;
    const date = new Date(dateValue);
    if (isNaN(date.getTime())) return null;
    return date.toLocaleDateString(i18n.language === "vi" ? "vi-VN" : "en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const displayDate =
    formatDate(entry.created_at) || formatDate(entry.last_seen_at);

  return (
    <Card
      className={`group transition-shadow hover:shadow-md ${className || ""}`}
      bodyStyle={{ padding: 16 }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0 space-y-2">
          {/* Sector Badge */}
          <div className="flex items-center gap-2 flex-wrap">
            <KnowledgeSectorBadge
              sector={entry.primary_sector}
              locale={i18n.language as "en" | "vi"}
            />
            {entry.tags.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {entry.tags.slice(0, 3).map((tag) => (
                  <Tag key={tag} size="small" color="grey">
                    {tag}
                  </Tag>
                ))}
                {entry.tags.length > 3 && (
                  <Tag size="small" color="grey">
                    +{entry.tags.length - 3}
                  </Tag>
                )}
              </div>
            )}
          </div>

          {/* Content */}
          <Paragraph className="text-sm whitespace-pre-wrap !mb-0">
            {truncatedContent}
          </Paragraph>

          {/* Metadata */}
          <div className="flex items-center gap-3">
            {displayDate && (
              <Text type="tertiary" size="small">{displayDate}</Text>
            )}
            {entry.salience > 0.5 && (
              <Text type="warning" size="small">{t("high_salience")}</Text>
            )}
          </div>
        </div>

        {/* Actions */}
        <Dropdown
          trigger="click"
          position="bottomRight"
          clickToHide
          render={
            <Dropdown.Menu>
              <Dropdown.Item onClick={handleCopy}>
                {isCopied ? <IconTick className="mr-2" /> : <IconCopy className="mr-2" />}
                {isCopied ? t("copied") : t("copy")}
              </Dropdown.Item>
              {onEdit && (
                <Dropdown.Item onClick={() => onEdit(entry)}>
                  <IconEdit className="mr-2" />
                  {t("edit")}
                </Dropdown.Item>
              )}
              {onDelete && (
                <Dropdown.Item type="danger" onClick={() => onDelete(entry.id)}>
                  <IconDelete className="mr-2" />
                  {t("delete")}
                </Dropdown.Item>
              )}
            </Dropdown.Menu>
          }
        >
          <Button
            icon={<IconMore />}
            theme="borderless"
            type="tertiary"
            size="small"
            className="opacity-0 group-hover:opacity-100 transition-opacity"
          />
        </Dropdown>
      </div>
    </Card>
  );
};
