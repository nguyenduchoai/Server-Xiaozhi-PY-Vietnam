/**
 * AudioFileUpload - Semi Design implementation
 */

import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Upload, X, Music } from "lucide-react";
import { Button, Typography, Spin } from "@douyinfe/semi-ui";

const { Text } = Typography;

interface AudioFileUploadProps {
    fieldName: string;
    label: string;
    description?: string;
    value?: string;
    onChange: (base64Value: string | null) => void;
    disabled?: boolean;
    accept?: string;
    error?: string;
    required?: boolean;
}

export function AudioFileUpload({
    fieldName,
    label,
    description,
    value,
    onChange,
    disabled = false,
    accept = ".wav,.mp3,.m4a,.ogg",
    error,
    required = false,
}: AudioFileUploadProps) {
    const { t } = useTranslation(["providers", "common"]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [fileName, setFileName] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [fileSize, setFileSize] = useState<number | null>(null);

    const hasValue = Boolean(value && value.length > 0);

    const handleFileChange = useCallback(
        async (event: React.ChangeEvent<HTMLInputElement>) => {
            const file = event.target.files?.[0];
            if (!file) return;

            const maxSize = 10 * 1024 * 1024;
            if (file.size > maxSize) {
                alert(t("providers:audio_file_too_large", "File quá lớn. Tối đa 10MB."));
                return;
            }

            setIsLoading(true);
            setFileName(file.name);
            setFileSize(file.size);

            try {
                const reader = new FileReader();
                reader.onload = () => {
                    const base64 = reader.result as string;
                    const base64Data = base64.split(",")[1];
                    onChange(base64Data);
                    setIsLoading(false);
                };
                reader.onerror = () => {
                    console.error("Error reading file");
                    setIsLoading(false);
                    alert(t("providers:audio_file_read_error", "Không thể đọc file. Vui lòng thử lại."));
                };
                reader.readAsDataURL(file);
            } catch (err) {
                console.error("Error processing file:", err);
                setIsLoading(false);
            }
        },
        [onChange, t]
    );

    const handleRemove = useCallback(() => {
        onChange(null);
        setFileName(null);
        setFileSize(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }, [onChange]);

    const handleClick = useCallback(() => {
        if (!disabled && fileInputRef.current) {
            fileInputRef.current.click();
        }
    }, [disabled]);

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    return (
        <div className="space-y-2">
            <Text strong size="small">
                {label}
                {required && <span className="ml-1 text-red-500">*</span>}
            </Text>

            {description && (
                <Text type="tertiary" size="small" className="block">
                    {description}
                </Text>
            )}

            <div className="flex flex-col gap-2">
                <input
                    ref={fileInputRef}
                    type="file"
                    id={fieldName}
                    accept={accept}
                    onChange={handleFileChange}
                    disabled={disabled || isLoading}
                    className="hidden"
                />

                {!hasValue && !fileName ? (
                    <button
                        type="button"
                        onClick={handleClick}
                        disabled={disabled || isLoading}
                        className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 p-6 transition-colors hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {isLoading ? (
                            <Spin />
                        ) : (
                            <>
                                <Upload className="h-8 w-8 text-gray-400" />
                                <Text type="tertiary">
                                    {t("providers:click_to_upload_audio", "Click để upload file audio")}
                                </Text>
                                <Text type="tertiary" size="small">
                                    WAV, MP3, M4A, OGG (max 10MB)
                                </Text>
                            </>
                        )}
                    </button>
                ) : (
                    <div className="flex items-center justify-between gap-3 rounded-lg border bg-gray-50 dark:bg-gray-800/50 p-3">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/30">
                                <Music className="h-5 w-5 text-blue-500" />
                            </div>
                            <div className="flex flex-col">
                                <Text strong>
                                    {fileName || t("providers:audio_uploaded", "Audio đã upload")}
                                </Text>
                                {fileSize && (
                                    <Text type="tertiary" size="small">{formatFileSize(fileSize)}</Text>
                                )}
                                {hasValue && !fileSize && (
                                    <Text type="success" size="small">
                                        ✓ {t("providers:audio_configured", "Đã cấu hình")}
                                    </Text>
                                )}
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <Button
                                size="small"
                                theme="borderless"
                                onClick={handleClick}
                                disabled={disabled || isLoading}
                            >
                                {t("common:change", "Thay đổi")}
                            </Button>
                            <Button
                                size="small"
                                theme="borderless"
                                type="danger"
                                icon={<X className="h-4 w-4" />}
                                onClick={handleRemove}
                                disabled={disabled || isLoading}
                            />
                        </div>
                    </div>
                )}
            </div>

            {error && <Text type="danger" size="small">{error}</Text>}
        </div>
    );
}
