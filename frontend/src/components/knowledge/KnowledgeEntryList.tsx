/**
 * KnowledgeEntryList - Semi Design implementation
 */

import { useTranslation } from "react-i18next";
import { Brain } from "lucide-react";
import { KnowledgeEntryCard } from "./KnowledgeEntryCard";
import { Button, Skeleton, Typography } from "@douyinfe/semi-ui";
import { IconPlus } from "@douyinfe/semi-icons";
import type { KnowledgeEntry } from "@/types";

const { Title, Text } = Typography;

type KnowledgeEntryListProps = {
  entries: KnowledgeEntry[];
  isLoading?: boolean;
  onEdit?: (entry: KnowledgeEntry) => void;
  onDelete?: (entryId: string) => void;
  onAddNew?: () => void;
  emptyMessage?: string;
};

export const KnowledgeEntryList = ({
  entries,
  isLoading = false,
  onEdit,
  onDelete,
  onAddNew,
  emptyMessage,
}: KnowledgeEntryListProps) => {
  const { t } = useTranslation("agents");

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton.Paragraph key={i} rows={3} />
        ))}
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center border rounded-lg border-dashed border-gray-300 dark:border-gray-700">
        <Brain className="h-12 w-12 text-gray-300 mb-4" />
        <Title heading={5} className="!mb-2">
          {emptyMessage || t("no_knowledge_entries")}
        </Title>
        <Text type="tertiary" className="mb-4 max-w-md">
          {t("no_knowledge_entries_desc")}
        </Text>
        {onAddNew && (
          <Button
            icon={<IconPlus />}
            theme="solid"
            type="primary"
            onClick={onAddNew}
          >
            {t("add_first_entry")}
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <KnowledgeEntryCard
          key={entry.id}
          entry={entry}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};
