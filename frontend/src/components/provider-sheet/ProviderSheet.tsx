"use client";

/**
 * ProviderSheet - Semi Design implementation
 */

import { memo, useCallback, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Copy, Trash2 } from "lucide-react";

import type { Provider, ProviderCategory } from "@types";
import { useProviderSheetStore } from "@/store/provider-sheet.store";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import {
  useProviderSchemaCategories,
  useValidateProviderConfig,
  useTestProviderConnection,
  useTestProviderReference,
} from "@/queries";
import { SideSheet, Button, Skeleton, Typography } from "@douyinfe/semi-ui";
import { ProviderCategoryTabs } from "./ProviderCategoryTabs";

const { Title, Text } = Typography;

export interface ProviderSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "update";
  provider?: Provider | null;
  initialCategory?: ProviderCategory | null;
  onSubmit: (data: {
    name: string;
    category: ProviderCategory;
    type: string;
    config: Record<string, unknown>;
    is_active?: boolean;
  }) => Promise<void>;
  onDuplicate?: (provider: Provider) => void;
  onDelete?: (provider: Provider) => void;
  isLoading?: boolean;
}

function ProviderSheetComponent({
  open,
  onOpenChange,
  mode,
  provider,
  initialCategory,
  onSubmit,
  onDuplicate,
  onDelete,
  isLoading = false,
}: ProviderSheetProps) {
  const { t } = useTranslation(["providers", "common"]);
  const { toast } = useToast();

  const {
    selectedCategory,
    selectedType,
    formValues,
    openSheet,
    closeSheet,
    setErrors,
    setValidationResult,
    setTestResult,
  } = useProviderSheetStore();

  const { user } = useAuth();
  const isSuperAdmin = user?.is_superuser === true;

  // Both 'default' (from config.yml), 'public' (shared DB providers), and is_public=true are non-editable/deletable
  const isDefaultProvider = provider?.source === "default" || provider?.source === "public" || provider?.is_public === true;
  const isReadOnly = false;

  const canEdit = isDefaultProvider || (!isDefaultProvider && (isSuperAdmin || (provider?.permissions?.includes("edit") ?? true)));
  const canTest = provider?.permissions?.includes("test") ?? true;
  const canDelete = !isDefaultProvider && (isSuperAdmin || (provider?.permissions?.includes("delete") ?? true));

  const { data: schemaData, isLoading: isSchemaLoading } =
    useProviderSchemaCategories();

  const { mutate: validateConfig, isPending: isValidating } =
    useValidateProviderConfig();
  const { mutate: testConnection, isPending: isTesting } =
    useTestProviderConnection();
  const { mutate: testReference, isPending: isTestingReference } =
    useTestProviderReference();

  const selectedFields = useMemo(() => {
    if (!schemaData?.data || !selectedCategory || !selectedType) return [];
    const typeSchema =
      schemaData.data[selectedCategory as keyof typeof schemaData.data]?.[
      selectedType as keyof (typeof schemaData.data)[keyof typeof schemaData.data]
      ];
    return typeSchema?.fields ?? [];
  }, [schemaData, selectedCategory, selectedType]);

  useEffect(() => {
    if (open) {
      openSheet(mode, provider ?? undefined, initialCategory ?? undefined);
    } else {
      closeSheet();
    }
  }, [open, mode, provider, initialCategory, openSheet, closeSheet]);

  const isFormDisabled =
    isLoading || isValidating || isTesting || isTestingReference;
  const isInputsDisabled = isFormDisabled || (mode === "update" && !canEdit);
  const canSubmit = Boolean(
    selectedCategory &&
    selectedType &&
    formValues.name &&
    !isReadOnly &&
    canEdit
  );
  const canTestConnection = isReadOnly
    ? canTest && Boolean(provider?.reference)
    : Boolean(selectedCategory && selectedType);

  const validateForm = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formValues.name || String(formValues.name).trim() === "") {
      newErrors.name = t("providers:name_required");
    }

    selectedFields.forEach((field) => {
      if (field.required) {
        const value = formValues[field.name];
        if (value === undefined || value === null || value === "") {
          newErrors[field.name] = `${field.label} is required`;
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formValues, selectedFields, setErrors, t]);

  const handleValidate = useCallback(() => {
    if (!selectedCategory || !selectedType || !validateForm()) return;

    const config = Object.fromEntries(
      Object.entries(formValues).filter(([key]) => key !== "name")
    );

    const { selectedTools: currentSelectedTools } =
      useProviderSheetStore.getState();

    const finalConfig = { ...config };
    if (selectedCategory === "Intent" && currentSelectedTools.length > 0) {
      finalConfig.functions = currentSelectedTools;
    }

    validateConfig(
      {
        category: selectedCategory,
        type: selectedType,
        config: finalConfig as Record<string, unknown>,
      },
      {
        onSuccess: (result) => {
          setValidationResult({
            valid: result.valid,
            errors: result.errors,
          });
        },
        onError: (error) => {
          setValidationResult({
            valid: false,
            errors: [error.message],
          });
        },
      }
    );
  }, [
    selectedCategory,
    selectedType,
    formValues,
    validateForm,
    validateConfig,
    setValidationResult,
  ]);

  const handleTestConnection = useCallback(() => {
    if (isReadOnly && provider?.reference) {
      const { testInputData } = useProviderSheetStore.getState();
      testReference(
        {
          reference: provider.reference,
          input_data: testInputData,
        },
        {
          onSuccess: (result) => {
            setValidationResult({
              valid: result.valid,
              errors: result.errors,
            });
            if (result.test_result) {
              setTestResult({
                success: result.test_result.success,
                message: result.test_result.message,
                error: result.test_result.error,
                latency_ms: result.test_result.latency_ms,
                text_output: result.test_result.output?.text,
                audio_base64: result.test_result.output?.audio_base64,
                audio_format: result.test_result.output?.audio_format,
              });
            }
          },
          onError: (error) => {
            setTestResult({
              success: false,
              error: error.message,
            });
          },
        }
      );
      return;
    }

    if (!selectedCategory || !selectedType || !validateForm()) return;

    const config = Object.fromEntries(
      Object.entries(formValues).filter(([key]) => key !== "name")
    );
    const { testInputData, selectedTools: currentSelectedTools } =
      useProviderSheetStore.getState();

    const finalConfig = { ...config };
    if (selectedCategory === "Intent" && currentSelectedTools.length > 0) {
      finalConfig.functions = currentSelectedTools;
    }

    testConnection(
      {
        category: selectedCategory,
        type: selectedType,
        config: finalConfig as Record<string, unknown>,
        input_data: testInputData,
      },
      {
        onSuccess: (result) => {
          setValidationResult({
            valid: result.valid,
            errors: result.errors,
          });
          setTestResult({
            success: result.test_result.success,
            message: result.test_result.message,
            error: result.test_result.error,
            latency_ms: result.test_result.latency_ms,
            text_output: result.test_result.output?.text,
            audio_base64: result.test_result.output?.audio_base64,
            audio_format: result.test_result.output?.audio_format,

          });
        },
        onError: (error) => {
          setTestResult({
            success: false,
            error: error.message,
          });
        },
      }
    );
  }, [
    isReadOnly,
    provider?.reference,
    selectedCategory,
    selectedType,
    formValues,
    validateForm,
    testReference,
    testConnection,
    setValidationResult,
    setTestResult,
  ]);

  const handleFormSubmit = useCallback(async () => {
    if (!selectedCategory || !selectedType || !validateForm()) return;

    const {
      formValues: currentFormValues,
      selectedTools: currentSelectedTools,
    } = useProviderSheetStore.getState();

    const { name, ...config } = currentFormValues;

    const finalConfig = { ...config };
    if (selectedCategory === "Intent" && currentSelectedTools.length > 0) {
      finalConfig.functions = currentSelectedTools;
    }

    const isDefaultConfig = provider?.source === "default";

    try {
      if (isDefaultConfig) {
        await onSubmit({
          name: String(name),
          category: selectedCategory,
          type: selectedType,
          config: finalConfig,
          is_active: true,
        });
      } else {
        await onSubmit({
          name: String(name),
          category: selectedCategory,
          type: selectedType,
          config: finalConfig,
          is_active: provider?.is_active ?? true,
        });
      }

      toast({
        title: t("common:success", "Thành công"),
        description: t("providers:saved_successfully", "Đã lưu cấu hình thành công"),
        variant: "default",
      });

    } catch (error) {
      console.error("Save failed:", error);
      toast({
        title: t("common:error", "Lỗi"),
        description: t("providers:save_failed", "Lưu thất bại"),
        variant: "destructive",
      });
    }
  }, [selectedCategory, selectedType, validateForm, onSubmit, provider, t, toast]);

  const handleDuplicate = useCallback(() => {
    if (!provider || !onDuplicate) return;

    const duplicateProvider: Provider = {
      ...provider,
      id: "",
      name: `${formValues.name || provider.name} (Copy)`,
      config: { ...provider.config },
      source: "user",
      permissions: ["edit", "delete", "test"],
    };

    selectedFields.forEach((field) => {
      if (formValues[field.name] !== undefined) {
        duplicateProvider.config[field.name] = formValues[field.name];
      }
    });

    onDuplicate(duplicateProvider);
  }, [provider, onDuplicate, formValues, selectedFields]);

  return (
    <SideSheet
      title={
        <Title heading={5} className="!mb-0">
          {mode === "create"
            ? t("providers:create_provider")
            : t("providers:update_provider")}
        </Title>
      }
      visible={open}
      onCancel={() => onOpenChange(false)}
      width={500}
      footer={
        <div className="flex flex-wrap gap-2">
          {/* Delete Button */}
          {mode === "update" && onDelete && canDelete && provider && (
            <Button
              type="danger"
              theme="solid"
              onClick={() => {
                onDelete(provider);
              }}
              disabled={isFormDisabled}
              icon={<Trash2 className="h-4 w-4" />}
            >
              {t("common:delete")}
            </Button>
          )}

          {/* Duplicate Button */}
          {mode === "update" && onDuplicate && (
            <Button
              onClick={handleDuplicate}
              disabled={isFormDisabled}
              icon={<Copy className="h-4 w-4" />}
            >
              {t("providers:duplicate")}
            </Button>
          )}

          {/* Validate Button */}
          {!isReadOnly && (
            <Button
              onClick={handleValidate}
              disabled={!canSubmit || isFormDisabled}
              loading={isValidating}
            >
              {t("providers:validate")}
            </Button>
          )}

          {/* Test Connection Button */}
          <Button
            onClick={handleTestConnection}
            disabled={!canTestConnection || isTesting || isTestingReference}
            loading={isTesting || isTestingReference}
          >
            {t("providers:test_connection")}
          </Button>

          {/* Save Button */}
          {!isReadOnly && canEdit && (
            <Button
              theme="solid"
              type="primary"
              onClick={handleFormSubmit}
              disabled={!canSubmit || isFormDisabled}
              loading={isLoading}
            >
              {t("common:save", "Lưu")}
            </Button>
          )}
        </div>
      }
    >
      <Text type="tertiary" className="block mb-4">
        {isReadOnly
          ? t("providers:default_provider_readonly")
          : mode === "create"
            ? t("providers:create_provider_description")
            : t("providers:update_provider_description")}
      </Text>

      {isSchemaLoading ? (
        <div className="space-y-4">
          <Skeleton.Paragraph rows={1} />
          <Skeleton.Paragraph rows={1} />
          <Skeleton.Paragraph rows={3} />
        </div>
      ) : (
        <div className="space-y-6">
          <ProviderCategoryTabs
            schemaData={schemaData?.data}
            isFormDisabled={isInputsDisabled}
          />
        </div>
      )}
    </SideSheet>
  );
}

export const ProviderSheet = memo(ProviderSheetComponent);
