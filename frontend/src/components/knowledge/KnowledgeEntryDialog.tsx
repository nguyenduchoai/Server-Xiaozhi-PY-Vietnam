/**
 * KnowledgeEntryDialog - Semi Design implementation
 */

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal, TextArea, Input, Button, Select, Typography } from "@douyinfe/semi-ui";
import { ALL_SECTORS, KnowledgeSectorBadge } from "./KnowledgeSectorBadge";
import type { KnowledgeEntry, MemorySector } from "@/types";

const { Title, Text } = Typography;

const formSchema = z.object({
  content: z
    .string()
    .min(1, "Content is required")
    .max(50000, "Content must be less than 50000 characters"),
  sector: z.enum([
    "episodic",
    "semantic",
    "procedural",
    "emotional",
    "reflective",
  ]),
  tags: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

type KnowledgeEntryDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entry?: KnowledgeEntry | null;
  onSubmit: (data: {
    content: string;
    sector: MemorySector;
    tags: string[];
  }) => Promise<void>;
  isLoading?: boolean;
};

export const KnowledgeEntryDialog = ({
  open,
  onOpenChange,
  entry,
  onSubmit,
  isLoading = false,
}: KnowledgeEntryDialogProps) => {
  const { t, i18n } = useTranslation("agents");
  const [error, setError] = useState<string | null>(null);
  const isEditMode = Boolean(entry);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      content: "",
      sector: "semantic",
      tags: "",
    },
  });

  useEffect(() => {
    if (open) {
      if (entry) {
        reset({
          content: entry.content,
          sector: entry.primary_sector,
          tags: entry.tags.join(", "),
        });
      } else {
        reset({
          content: "",
          sector: "semantic",
          tags: "",
        });
      }
      setError(null);
    }
  }, [open, entry, reset]);

  const onFormSubmit = async (values: FormValues) => {
    setError(null);
    try {
      const tags = values.tags
        ? values.tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean)
        : [];

      await onSubmit({
        content: values.content,
        sector: values.sector as MemorySector,
        tags,
      });

      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error_saving_entry"));
    }
  };

  const sectorOptions = ALL_SECTORS.map((sector) => ({
    value: sector,
    label: <KnowledgeSectorBadge sector={sector} locale={i18n.language as "en" | "vi"} />,
  }));

  return (
    <Modal
      title={
        <Title heading={5} className="!mb-0">
          {isEditMode ? t("edit_knowledge_entry") : t("add_knowledge_entry")}
        </Title>
      }
      visible={open}
      onCancel={() => onOpenChange(false)}
      footer={
        <div className="flex justify-end gap-2">
          <Button onClick={() => onOpenChange(false)} disabled={isLoading}>
            {t("cancel")}
          </Button>
          <Button
            theme="solid"
            type="primary"
            onClick={handleSubmit(onFormSubmit)}
            loading={isLoading}
          >
            {isLoading
              ? t("saving")
              : isEditMode
                ? t("save_changes")
                : t("create")}
          </Button>
        </div>
      }
      width={600}
    >
      <Text type="tertiary" className="block mb-4">
        {isEditMode ? t("edit_knowledge_entry_desc") : t("add_knowledge_entry_desc")}
      </Text>

      <div className="space-y-4">
        {/* Content */}
        <div className="space-y-2">
          <Text strong size="small">{t("content")}</Text>
          <Controller
            name="content"
            control={control}
            render={({ field }) => (
              <TextArea
                {...field}
                placeholder={t("enter_knowledge_content")}
                rows={6}
                autosize={false}
              />
            )}
          />
          {errors.content && (
            <Text type="danger" size="small">{errors.content.message}</Text>
          )}
        </div>

        {/* Sector */}
        <div className="space-y-2">
          <Text strong size="small">{t("sector")}</Text>
          <Controller
            name="sector"
            control={control}
            render={({ field }) => (
              <Select
                style={{ width: "100%" }}
                value={field.value}
                onChange={(v) => field.onChange(v)}
                optionList={sectorOptions}
                placeholder={t("select_sector")}
              />
            )}
          />
          {errors.sector && (
            <Text type="danger" size="small">{errors.sector.message}</Text>
          )}
        </div>

        {/* Tags */}
        <div className="space-y-2">
          <Text strong size="small">{t("tags_optional")}</Text>
          <Controller
            name="tags"
            control={control}
            render={({ field }) => (
              <Input
                {...field}
                placeholder={t("enter_tags_placeholder")}
              />
            )}
          />
        </div>

        {error && <Text type="danger" size="small">{error}</Text>}
      </div>
    </Modal>
  );
};
