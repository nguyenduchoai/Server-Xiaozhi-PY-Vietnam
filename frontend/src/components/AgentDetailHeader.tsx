/**
 * AgentDetailHeader - Semi Design implementation
 * Header with agent avatar, name, status and action buttons
 */

import { memo, useCallback } from "react";
import { useTranslation } from "react-i18next";

import type { AgentStatus } from "@types";
import { Button, Tag, Dropdown, Typography } from "@douyinfe/semi-ui";
import { IconMore, IconDelete, IconEdit } from "@douyinfe/semi-icons";
import { AvatarUpload } from "./AvatarUpload";

const { Title } = Typography;

export interface AgentDetailHeaderProps {
  agentId: string;
  agentName: string;
  status: AgentStatus;
  avatarUrl?: string | null;
  onEdit?: () => void;
  onDelete?: () => void;
  onAvatarChange?: (newUrl: string | null) => void;
  isDeleting?: boolean;
}

const AgentDetailHeaderComponent = ({
  agentId,
  agentName,
  status,
  avatarUrl,
  onEdit,
  onDelete,
  onAvatarChange,
  isDeleting = false,
}: AgentDetailHeaderProps) => {
  const { t } = useTranslation("agents");

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
          uploadPath={`/agents/${agentId}/avatar`}
          onUploadSuccess={handleAvatarUpload}
          onDeleteSuccess={handleAvatarDelete}
          size={80}
          placeholder={t("upload_avatar", "Tải ảnh")}
        />

        {/* Name & Status */}
        <div className="flex-1 min-w-0">
          <Title heading={2} className="!mb-0 truncate">
            {agentName}
          </Title>
          <div className="mt-2 flex items-center gap-3">
            <Tag
              color={status === "enabled" ? "green" : "grey"}
              size="large"
              className="capitalize"
            >
              {status === "enabled" ? "Enabled" : status}
            </Tag>
            {onDelete && (
              <Button
                type="danger"
                theme="solid"
                size="small"
                icon={<IconDelete />}
                onClick={handleDelete}
                disabled={isDeleting}
                loading={isDeleting}
              >
                {isDeleting ? t("deleting") : t("delete_agent", "Xóa Agent")}
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">


        <Button
          theme="light"
          size="default"
          icon={<IconEdit />}
          onClick={handleEdit}
          disabled={isDeleting}
          className="hidden sm:flex"
        >
          {t("edit", "Sửa")}
        </Button>

        <Dropdown
          trigger="click"
          position="bottomRight"
          clickToHide
          render={
            <Dropdown.Menu>

              <Dropdown.Item onClick={handleEdit} disabled={isDeleting} className="sm:hidden">
                <IconEdit className="mr-2" />
                {t("edit", "Sửa")}
              </Dropdown.Item>
              <Dropdown.Divider className="sm:hidden" />
              <Dropdown.Item
                type="danger"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                <IconDelete className="mr-2" />
                {isDeleting ? t("deleting") : t("delete")}
              </Dropdown.Item>
            </Dropdown.Menu>
          }
        >
          <Button
            icon={<IconMore />}
            theme="borderless"
            type="tertiary"
            disabled={isDeleting}
          />
        </Dropdown>
      </div>
    </div>
  );
};

export const AgentDetailHeader = memo(AgentDetailHeaderComponent);

