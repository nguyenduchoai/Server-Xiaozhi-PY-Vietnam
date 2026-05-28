/**
 * KnowledgeAddMenu - Semi Design implementation
 */

import { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, Upload } from "lucide-react";
import { Button, Dropdown, Modal, Input, Select, Card, Typography } from "@douyinfe/semi-ui";
import { IconPlus, IconFile, IconLink, IconEdit } from "@douyinfe/semi-icons";
import { ALL_SECTORS, KnowledgeSectorBadge } from "./KnowledgeSectorBadge";
import type { MemorySector, IngestFilePayload, IngestUrlPayload } from "@/types";

const { Text } = Typography;

type KnowledgeAddMenuProps = {
  onAddManual: () => void;
  onIngestFile: (payload: IngestFilePayload) => Promise<void>;
  onIngestUrl: (payload: IngestUrlPayload) => Promise<void>;
  isLoading?: boolean;
};

const SUPPORTED_FILE_TYPES = {
  "application/pdf": "pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
  "text/plain": "txt",
  "text/markdown": "md",
} as const;

const ACCEPTED_EXTENSIONS = ".pdf,.docx,.txt,.md";

export function KnowledgeAddMenu({
  onAddManual,
  onIngestFile,
  onIngestUrl,
  isLoading = false,
}: KnowledgeAddMenuProps) {
  const { t, i18n } = useTranslation("agents");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isUrlDialogOpen, setIsUrlDialogOpen] = useState(false);
  const [isFileDialogOpen, setIsFileDialogOpen] = useState(false);

  const [url, setUrl] = useState("");
  const [urlSector, setUrlSector] = useState<MemorySector>("semantic");
  const [urlTags, setUrlTags] = useState("");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileSector, setFileSector] = useState<MemorySector>("semantic");
  const [fileTags, setFileTags] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);

  const resetUrlForm = () => {
    setUrl("");
    setUrlSector("semantic");
    setUrlTags("");
  };

  const resetFileForm = () => {
    setSelectedFile(null);
    setFileSector("semantic");
    setFileTags("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setIsFileDialogOpen(true);
    }
  };

  const handleFileButtonClick = () => {
    fileInputRef.current?.click();
  };

  const getFileContentType = (file: File): IngestFilePayload["content_type"] | null => {
    const mimeType = file.type as keyof typeof SUPPORTED_FILE_TYPES;
    if (SUPPORTED_FILE_TYPES[mimeType]) {
      return SUPPORTED_FILE_TYPES[mimeType] as IngestFilePayload["content_type"];
    }
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext && ["pdf", "docx", "txt", "md"].includes(ext)) {
      return ext as IngestFilePayload["content_type"];
    }
    return null;
  };

  const parseTags = (tagsString: string): string[] => {
    return tagsString.split(",").map((tag) => tag.trim()).filter((tag) => tag.length > 0);
  };

  const handleUrlSubmit = async () => {
    if (!url.trim()) return;

    setIsSubmitting(true);
    try {
      await onIngestUrl({
        url: url.trim(),
        sector: urlSector,
        tags: parseTags(urlTags),
      });
      setIsUrlDialogOpen(false);
      resetUrlForm();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileSubmit = async () => {
    if (!selectedFile) return;

    const contentType = getFileContentType(selectedFile);
    if (!contentType) return;

    setIsSubmitting(true);
    try {
      const reader = new FileReader();
      const base64Data = await new Promise<string>((resolve, reject) => {
        reader.onload = () => {
          const result = reader.result as string;
          const base64 = result.split(",")[1] || result;
          resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(selectedFile);
      });

      await onIngestFile({
        content_type: contentType,
        data: base64Data,
        filename: selectedFile.name,
        sector: fileSector,
        tags: parseTags(fileTags),
      });
      setIsFileDialogOpen(false);
      resetFileForm();
    } finally {
      setIsSubmitting(false);
    }
  };

  const locale = i18n.language as "en" | "vi";

  const sectorOptions = ALL_SECTORS.map((sector) => ({
    value: sector,
    label: <KnowledgeSectorBadge sector={sector} locale={locale} />,
  }));

  return (
    <>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Add Menu Button */}
      <Dropdown
        trigger="click"
        position="bottomRight"
        clickToHide
        render={
          <Dropdown.Menu>
            <Dropdown.Item onClick={onAddManual}>
              <IconEdit className="mr-2" />
              {t("add_manual_entry")}
            </Dropdown.Item>
            <Dropdown.Divider />
            <Dropdown.Item onClick={handleFileButtonClick}>
              <IconFile className="mr-2" />
              {t("import_from_file")}
            </Dropdown.Item>
            <Dropdown.Item onClick={() => setIsUrlDialogOpen(true)}>
              <IconLink className="mr-2" />
              {t("import_from_url")}
            </Dropdown.Item>
          </Dropdown.Menu>
        }
      >
        <Button
          icon={<IconPlus />}
          theme="solid"
          type="primary"
          disabled={isLoading}
        >
          {t("add_knowledge")} <ChevronDown className="ml-1 h-3 w-3" />
        </Button>
      </Dropdown>

      {/* URL Dialog */}
      <Modal
        title={t("import_from_url")}
        visible={isUrlDialogOpen}
        onCancel={() => { setIsUrlDialogOpen(false); resetUrlForm(); }}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => { setIsUrlDialogOpen(false); resetUrlForm(); }}>
              {t("cancel")}
            </Button>
            <Button
              theme="solid"
              type="primary"
              onClick={handleUrlSubmit}
              loading={isSubmitting}
              disabled={!url.trim() || isSubmitting}
            >
              {t("import")}
            </Button>
          </div>
        }
      >
        <Text type="tertiary" className="block mb-4">{t("import_url_description")}</Text>
        <div className="space-y-4">
          <div>
            <Text strong size="small" className="block mb-1.5">{t("url")}</Text>
            <Input
              placeholder="https://example.com/article"
              value={url}
              onChange={setUrl}
            />
          </div>
          <div>
            <Text strong size="small" className="block mb-1.5">{t("sector")}</Text>
            <Select
              style={{ width: "100%" }}
              value={urlSector}
              onChange={(v) => setUrlSector(v as MemorySector)}
              optionList={sectorOptions}
            />
          </div>
          <div>
            <Text strong size="small" className="block mb-1.5">{t("tags_optional")}</Text>
            <Input
              placeholder={t("tags_placeholder")}
              value={urlTags}
              onChange={setUrlTags}
            />
          </div>
        </div>
      </Modal>

      {/* File Dialog */}
      <Modal
        title={t("import_from_file")}
        visible={isFileDialogOpen}
        onCancel={() => { setIsFileDialogOpen(false); resetFileForm(); }}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => { setIsFileDialogOpen(false); resetFileForm(); }}>
              {t("cancel")}
            </Button>
            <Button
              theme="solid"
              type="primary"
              onClick={handleFileSubmit}
              loading={isSubmitting}
              disabled={!selectedFile || isSubmitting}
            >
              {t("import")}
            </Button>
          </div>
        }
      >
        <Text type="tertiary" className="block mb-4">{t("import_file_description")}</Text>
        <div className="space-y-4">
          {selectedFile && (
            <Card className="!bg-gray-50 dark:!bg-gray-800" bodyStyle={{ padding: 12 }}>
              <div className="flex items-center gap-3">
                <Upload className="h-5 w-5 text-gray-400" />
                <div className="flex-1 min-w-0">
                  <Text strong className="block truncate">{selectedFile.name}</Text>
                  <Text type="tertiary" size="small">
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </Text>
                </div>
                <Button size="small" onClick={handleFileButtonClick}>
                  {t("change")}
                </Button>
              </div>
            </Card>
          )}
          <div>
            <Text strong size="small" className="block mb-1.5">{t("sector")}</Text>
            <Select
              style={{ width: "100%" }}
              value={fileSector}
              onChange={(v) => setFileSector(v as MemorySector)}
              optionList={sectorOptions}
            />
          </div>
          <div>
            <Text strong size="small" className="block mb-1.5">{t("tags_optional")}</Text>
            <Input
              placeholder={t("tags_placeholder")}
              value={fileTags}
              onChange={setFileTags}
            />
          </div>
        </div>
      </Modal>
    </>
  );
}
