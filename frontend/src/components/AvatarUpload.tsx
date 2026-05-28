/**
 * AvatarUpload - Semi Design component for uploading agent/template avatars
 * Features:
 * - Click to upload image
 * - Preview with hover effect
 * - Delete option
 * - Optimized for device display (shown as 256x256 max)
 */

import { useState, useCallback, memo } from "react";
import { useTranslation } from "react-i18next";
import { Upload, Avatar, Toast, Spin, Button, Popconfirm } from "@douyinfe/semi-ui";
import { IconCamera, IconDelete, IconUpload } from "@douyinfe/semi-icons";

export interface AvatarUploadProps {
    /** Current avatar URL */
    avatarUrl?: string | null;
    /** Upload endpoint path (e.g., "/agents/{id}/avatar") */
    uploadPath: string;
    /** Callback when avatar is uploaded successfully */
    onUploadSuccess?: (newAvatarUrl: string) => void;
    /** Callback when avatar is deleted */
    onDeleteSuccess?: () => void;
    /** Size of avatar preview (default: 120) */
    size?: number;
    /** Custom placeholder text */
    placeholder?: string;
    /** Whether to show delete button */
    showDelete?: boolean;
    /** Custom class name */
    className?: string;
}

const AvatarUploadComponent = ({
    avatarUrl,
    uploadPath,
    onUploadSuccess,
    onDeleteSuccess,
    size = 120,
    placeholder,
    showDelete = true,
    className = "",
}: AvatarUploadProps) => {
    const { t } = useTranslation("common");
    const [uploading, setUploading] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [hover, setHover] = useState(false);

    // Get full URL for display
    const displayUrl = avatarUrl ?
        (avatarUrl.startsWith("http") ? avatarUrl : `${window.location.origin}${avatarUrl}`)
        : null;

    // Custom upload handler - using any for Semi Design compatibility
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const customRequest = useCallback(
        async (args: any) => {
            const { file, onSuccess, onError } = args;
            setUploading(true);
            try {
                const formData = new FormData();
                formData.append("file", file.fileInstance as File);

                const response = await fetch(`/api/v1${uploadPath}`, {
                    method: "POST",
                    body: formData,
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
                    },
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || "Upload failed");
                }

                const data = await response.json();
                onSuccess?.(data);
                onUploadSuccess?.(data.avatar_url);
                Toast.success(t("avatar_uploaded", "Đã tải lên avatar"));
            } catch (error) {
                console.error("Upload error:", error);
                onError?.(error as Error);
                Toast.error((error as Error).message || t("upload_failed", "Tải lên thất bại"));
            } finally {
                setUploading(false);
            }
        },
        [uploadPath, onUploadSuccess, t]
    );

    // Delete avatar handler
    const handleDelete = useCallback(async () => {
        setDeleting(true);
        try {
            const response = await fetch(`/api/v1${uploadPath}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${localStorage.getItem("access_token")}`,
                },
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "Delete failed");
            }

            onDeleteSuccess?.();
            Toast.success(t("avatar_deleted", "Đã xóa avatar"));
        } catch (error) {
            console.error("Delete error:", error);
            Toast.error((error as Error).message || t("delete_failed", "Xóa thất bại"));
        } finally {
            setDeleting(false);
        }
    }, [uploadPath, onDeleteSuccess, t]);

    return (
        <div
            className={`relative inline-block ${className}`}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
        >
            <Upload
                accept="image/jpeg,image/png,image/webp,image/gif"
                showUploadList={false}
                customRequest={customRequest}
                disabled={uploading || deleting}
                limit={1}
            >
                <div
                    className="relative cursor-pointer group"
                    style={{ width: size, height: size }}
                >
                    {/* Avatar or Placeholder */}
                    <Avatar
                        src={displayUrl || undefined}
                        style={{
                            width: size,
                            height: size,
                            border: "2px dashed var(--semi-color-border)",
                            backgroundColor: "var(--semi-color-fill-0)",
                        }}
                    >
                        {!displayUrl && (
                            <IconCamera
                                size="extra-large"
                                style={{ color: "var(--semi-color-text-2)" }}
                            />
                        )}
                    </Avatar>

                    {/* Loading Overlay */}
                    {uploading && (
                        <div
                            className="absolute inset-0 flex items-center justify-center rounded-full"
                            style={{
                                backgroundColor: "rgba(0,0,0,0.5)",
                            }}
                        >
                            <Spin />
                        </div>
                    )}

                    {/* Hover Overlay */}
                    {!uploading && hover && (
                        <div
                            className="absolute inset-0 flex items-center justify-center rounded-full transition-opacity"
                            style={{
                                backgroundColor: "rgba(0,0,0,0.5)",
                            }}
                        >
                            <div className="text-center text-white">
                                <IconUpload size="large" />
                                <div className="text-xs mt-1">
                                    {placeholder || t("upload_avatar", "Tải ảnh")}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </Upload>

            {/* Delete Button */}
            {showDelete && displayUrl && !uploading && (
                <Popconfirm
                    title={t("confirm_delete_avatar", "Xóa avatar này?")}
                    onConfirm={handleDelete}
                    position="right"
                >
                    <Button
                        icon={<IconDelete />}
                        size="small"
                        type="danger"
                        theme="solid"
                        className="absolute -bottom-1 -right-1"
                        loading={deleting}
                        style={{
                            borderRadius: "50%",
                            width: 28,
                            height: 28,
                            minWidth: 28,
                            padding: 0,
                        }}
                    />
                </Popconfirm>
            )}
        </div>
    );
};

export const AvatarUpload = memo(AvatarUploadComponent);

export default AvatarUpload;
