/**
 * TemplateDetailHeader - Semi Design implementation
 * Header with template avatar, name, visibility and action buttons
 */

import { memo, useCallback } from "react";
import { Globe, Lock } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button, Tag, Typography } from "@douyinfe/semi-ui";
import { IconEdit, IconDelete } from "@douyinfe/semi-icons";
import { AvatarUpload } from "./AvatarUpload";

const { Title } = Typography;

export interface TemplateDetailHeaderProps {
  templateId: string;
  templateName: string;
  isPublic?: boolean;
  avatarUrl?: string | null;
  onEdit?: () => void;
  onDelete?: () => void;
  onAvatarChange?: (newUrl: string | null) => void;
  isDeleting?: boolean;
}

const TemplateDetailHeaderComponent = ({
  templateId,
  templateName,
  isPublic = false,
  avatarUrl,
  onEdit,
  onDelete,
  onAvatarChange,
  isDeleting = false,
}: TemplateDetailHeaderProps) => {
  const { t } = useTranslation("templates");

  const handleDelete = useCallback(() => {
    onDelete?.();
  }, [onDelete]);

  const handleEdit = useCallback(() => {
    onEdit?.();
  }, [onEdit]);

  const handleAvatarUpload = useCallback((newUrl: string) => {
    onAvatarChange?.(newUrl);
  }, [onAvatarChange]);

  const handleAvatarDelete = useCallback(() => {
    onAvatarChange?.(null);
  }, [onAvatarChange]);

  return (
    <div className="flex items-center justify-between gap-4 mb-6">
      {/* Avatar + Info Section */}
      <div className="flex items-center gap-4 flex-1 min-w-0">
        {/* Avatar Upload */}
        <AvatarUpload
          avatarUrl={avatarUrl}
          uploadPath={`/templates/${templateId}/avatar`}
          onUploadSuccess={handleAvatarUpload}
          onDeleteSuccess={handleAvatarDelete}
          size={80}
          placeholder={t("upload_avatar", "Tải ảnh")}
        />

        {/* Name & Status */}
        <div className="flex-1 min-w-0">
          <Title heading={2} className="!mb-0 truncate">
            {templateName}
          </Title>
          <div className="mt-2 flex items-center gap-2">
            <Tag color={isPublic ? "blue" : "grey"} size="large">
              {isPublic ? (
                <span className="flex items-center gap-1">
                  <Globe className="h-3 w-3" />
                  {t("public")}
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <Lock className="h-3 w-3" />
                  {t("private")}
                </span>
              )}
            </Tag>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          icon={<IconEdit />}
          theme="light"
          onClick={handleEdit}
          disabled={isDeleting}
        >
          {t("edit")}
        </Button>
        <Button
          icon={<IconDelete />}
          type="danger"
          theme="solid"
          onClick={handleDelete}
          disabled={isDeleting}
          loading={isDeleting}
        >
          {isDeleting ? t("deleting") : t("delete", "Xóa")}
        </Button>
      </div>
    </div>
  );
};

export const TemplateDetailHeader = memo(TemplateDetailHeaderComponent);

