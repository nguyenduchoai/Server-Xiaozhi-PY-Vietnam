/**
 * UserToolSheet - Beautiful Semi Design implementation
 * Create, Edit, View tool configurations
 */

import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { AlertCircle, Eye, EyeOff, Trash2, Wrench, Settings, Check } from "lucide-react";

import toolService, {
  type UserToolCreate,
  type UserToolUpdate,
  type ToolSchema,
  type ToolField,
} from "@/services/toolService";
import {
  SideSheet,
  Typography,
  Button,
  Select,
  Input,
  TextArea,
  Switch,
  Tag,
  Spin,
  Banner,
  Card,
  Modal,
  Toast,
  Divider,
} from "@douyinfe/semi-ui";
import { IconDelete, IconSave, IconClose } from "@douyinfe/semi-icons";

const { Title, Text, Paragraph } = Typography;

interface FormState {
  tool_name: string;
  name: string;
  description: string;
  config: Record<string, unknown>;
  is_active: boolean;
}

interface ValidationErrors {
  tool_name?: string;
  name?: string;
  config?: Record<string, string>;
}

export interface UserToolSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit" | "view";
  toolId?: string;
  onSuccess?: () => void;
  onDelete?: (toolId: string) => void;
}

const initialFormState: FormState = {
  tool_name: "",
  name: "",
  description: "",
  config: {},
  is_active: true,
};

export const UserToolSheet = ({
  open,
  onOpenChange,
  mode,
  toolId,
  onSuccess,
  onDelete,
}: UserToolSheetProps) => {
  const { t } = useTranslation(["tools", "common"]);

  // State
  const [form, setForm] = useState<FormState>(initialFormState);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [availableTools, setAvailableTools] = useState<ToolSchema[]>([]);
  const [selectedSchema, setSelectedSchema] = useState<ToolSchema | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  // Load available tools
  useEffect(() => {
    const loadTools = async () => {
      try {
        const response = await toolService.getAvailableTools();
        const configurableTools = response.data.filter((t) => t.requires_config);
        setAvailableTools(configurableTools);
      } catch (err) {
        console.error("Failed to load available tools:", err);
      }
    };
    loadTools();
  }, []);

  // Load existing tool config when editing
  useEffect(() => {
    if (!open) {
      setForm(initialFormState);
      setErrors({});
      setSelectedSchema(null);
      setLoadError(null);
      return;
    }

    if (mode === "create") {
      setForm(initialFormState);
      setSelectedSchema(null);
      return;
    }

    if (!toolId) return;

    const loadTool = async () => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const response = await toolService.getUserTool(toolId);
        const tool = response.data;
        setForm({
          tool_name: tool.tool_name,
          name: tool.name,
          description: tool.description || "",
          config: tool.config,
          is_active: tool.is_active,
        });

        const schemaResponse = await toolService.getToolSchema(tool.tool_name);
        setSelectedSchema(schemaResponse.data);
      } catch (err) {
        setLoadError(
          err instanceof Error ? err.message : "Failed to load tool configuration"
        );
      } finally {
        setIsLoading(false);
      }
    };
    loadTool();
  }, [open, mode, toolId]);

  // Load schema when tool_name changes (create mode)
  useEffect(() => {
    if (mode !== "create" || !form.tool_name) {
      return;
    }

    const loadSchema = async () => {
      try {
        const response = await toolService.getToolSchema(form.tool_name);
        setSelectedSchema(response.data);
        const defaultConfig: Record<string, unknown> = {};
        response.data.fields?.forEach((field) => {
          if (field.default !== null && field.default !== undefined) {
            defaultConfig[field.name] = field.default;
          }
        });
        setForm((prev) => ({ ...prev, config: defaultConfig }));
      } catch (err) {
        console.error("Failed to load tool schema:", err);
      }
    };
    loadSchema();
  }, [mode, form.tool_name]);

  // Validate form
  const validateForm = useCallback((): boolean => {
    const newErrors: ValidationErrors = {};

    if (!form.tool_name) {
      newErrors.tool_name = t("tools:select_tool");
    }

    if (!form.name.trim()) {
      newErrors.name = t("tools:config_name") + " is required";
    }

    if (selectedSchema?.fields) {
      const configErrors: Record<string, string> = {};
      selectedSchema.fields.forEach((field) => {
        if (field.required && !form.config[field.name]) {
          configErrors[field.name] = `${field.display_name} is required`;
        }
      });
      if (Object.keys(configErrors).length > 0) {
        newErrors.config = configErrors;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [form, selectedSchema, t]);

  // Handle save
  const handleSave = async () => {
    if (!validateForm()) return;

    setIsSaving(true);
    try {
      if (mode === "create") {
        const payload: UserToolCreate = {
          tool_name: form.tool_name,
          name: form.name,
          description: form.description || undefined,
          config: form.config,
          is_active: form.is_active,
        };
        await toolService.createUserTool(payload);
        Toast.success(t("common:created_success", "Tạo thành công!"));
      } else if (mode === "edit" && toolId) {
        const payload: UserToolUpdate = {
          name: form.name,
          description: form.description || undefined,
          config: form.config,
          is_active: form.is_active,
        };
        await toolService.updateUserTool(toolId, payload);
        Toast.success(t("common:saved_success", "Đã lưu!"));
      }
      onSuccess?.();
      onOpenChange(false);
    } catch (err) {
      console.error("Failed to save tool config:", err);
      Toast.error(err instanceof Error ? err.message : "Lỗi khi lưu");
    } finally {
      setIsSaving(false);
    }
  };

  // Handle delete
  const handleDelete = async () => {
    if (!toolId) return;
    try {
      await toolService.deleteUserTool(toolId);
      Toast.success(t("common:deleted_success", "Đã xóa!"));
      onDelete?.(toolId);
      onOpenChange(false);
    } catch (err) {
      Toast.error("Lỗi khi xóa");
    }
    setDeleteConfirmOpen(false);
  };

  // Render config field based on type
  const renderConfigField = (field: ToolField) => {
    const value = form.config[field.name];
    const error = errors.config?.[field.name];
    const isSecret = field.field_type === "secret";
    const showValue = showSecrets[field.name] || false;

    return (
      <div key={field.name} className="mb-4">
        <div className="flex items-center gap-1 mb-1.5">
          <Text strong className="text-sm">{field.display_name}</Text>
          {field.required && <Text type="danger" className="text-sm">*</Text>}
        </div>

        {field.field_type === "select" && field.options ? (
          <Select
            value={String(value || "")}
            onChange={(v) =>
              setForm((prev) => ({
                ...prev,
                config: { ...prev.config, [field.name]: v },
              }))
            }
            disabled={mode === "view"}
            placeholder={`Select ${field.display_name}`}
            style={{ width: "100%" }}
            optionList={field.options.map((opt) => ({ label: opt, value: opt }))}
          />
        ) : field.field_type === "boolean" ? (
          <div className="flex items-center gap-3">
            <Switch
              checked={Boolean(value)}
              onChange={(checked) =>
                setForm((prev) => ({
                  ...prev,
                  config: { ...prev.config, [field.name]: checked },
                }))
              }
              disabled={mode === "view"}
            />
            <Text type="tertiary" size="small">{field.description}</Text>
          </div>
        ) : field.field_type === "number" ? (
          <Input
            type="number"
            value={value !== undefined ? String(value) : ""}
            onChange={(v) =>
              setForm((prev) => ({
                ...prev,
                config: {
                  ...prev.config,
                  [field.name]: v ? Number(v) : undefined,
                },
              }))
            }
            placeholder={field.description}
            disabled={mode === "view"}
          />
        ) : (
          <Input
            type={isSecret && !showValue ? "password" : "text"}
            value={String(value || "")}
            onChange={(v) =>
              setForm((prev) => ({
                ...prev,
                config: { ...prev.config, [field.name]: v },
              }))
            }
            placeholder={field.description}
            disabled={mode === "view"}
            suffix={
              isSecret && (
                <button
                  type="button"
                  onClick={() =>
                    setShowSecrets((prev) => ({
                      ...prev,
                      [field.name]: !prev[field.name],
                    }))
                  }
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showValue ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              )
            }
          />
        )}

        {error && <Text type="danger" size="small" className="mt-1">{error}</Text>}
        {field.description && field.field_type !== "boolean" && (
          <Text type="tertiary" size="small" className="mt-1 block">{field.description}</Text>
        )}
      </div>
    );
  };

  const isViewMode = mode === "view";
  const title = mode === "create"
    ? t("tools:create_config")
    : mode === "edit"
      ? t("tools:edit_config")
      : t("tools:view_config");

  const getIcon = () => {
    if (mode === "create") return <Settings className="h-5 w-5 text-blue-500" />;
    if (mode === "edit") return <Wrench className="h-5 w-5 text-orange-500" />;
    return <Eye className="h-5 w-5 text-green-500" />;
  };

  return (
    <>
      <SideSheet
        title={
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30">
              {getIcon()}
            </div>
            <div>
              <Title heading={5} className="!mb-0">{title}</Title>
              <Text type="tertiary" size="small">
                {mode === "create"
                  ? t("tools:create_config_description")
                  : t("tools:config_description")}
              </Text>
            </div>
          </div>
        }
        visible={open}
        onCancel={() => onOpenChange(false)}
        width={480}
        footer={
          <div className="flex items-center gap-3 p-4 border-t bg-gray-50 dark:bg-gray-900 -mx-6 -mb-4">
            {mode === "edit" && (
              <Button
                icon={<IconDelete />}
                type="danger"
                theme="borderless"
                onClick={() => setDeleteConfirmOpen(true)}
                disabled={isSaving}
              >
                {t("common:delete", "Xóa")}
              </Button>
            )}
            <div className="flex-1" />
            <Button
              icon={<IconClose />}
              theme="borderless"
              onClick={() => onOpenChange(false)}
            >
              {isViewMode ? t("common:close", "Đóng") : t("common:cancel", "Hủy")}
            </Button>
            {!isViewMode && (
              <Button
                icon={<IconSave />}
                theme="solid"
                type="primary"
                onClick={handleSave}
                loading={isSaving}
              >
                {mode === "create" ? t("common:create", "Tạo") : t("common:save", "Lưu")}
              </Button>
            )}
          </div>
        }
        bodyStyle={{ padding: "24px" }}
      >
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Spin size="large" />
          </div>
        ) : loadError ? (
          <Banner type="danger" description={loadError} icon={<AlertCircle />} className="mb-4" />
        ) : (
          <div className="space-y-6">
            {/* Tool Selection (only in create mode) */}
            {mode === "create" && (
              <Card
                className="!rounded-xl border-dashed"
                bodyStyle={{ padding: 16 }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <Wrench className="h-4 w-4 text-blue-500" />
                  <Text strong>{t("tools:select_tool")}</Text>
                  <Text type="danger">*</Text>
                </div>
                <Select
                  value={form.tool_name}
                  onChange={(v) =>
                    setForm((prev) => ({ ...prev, tool_name: v as string, name: "", config: {} }))
                  }
                  placeholder={t("tools:select_tool_placeholder")}
                  style={{ width: "100%" }}
                  optionList={availableTools.map((tool) => ({
                    label: (
                      <div className="py-1">
                        <div className="font-medium">{tool.display_name}</div>
                        <div className="text-xs text-gray-500">{tool.description}</div>
                      </div>
                    ),
                    value: tool.name,
                  }))}
                  renderSelectedItem={(optionNode: { value?: string } | null) => (
                    <div className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500" />
                      {availableTools.find((t) => t.name === optionNode?.value)?.display_name || optionNode?.value}
                    </div>
                  )}
                />
                {errors.tool_name && (
                  <Text type="danger" size="small" className="mt-1">{errors.tool_name}</Text>
                )}
              </Card>
            )}

            {/* Show tool info in edit/view mode */}
            {mode !== "create" && selectedSchema && (
              <Card
                className="!rounded-xl bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-0"
                bodyStyle={{ padding: 16 }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-2xl">🛠️</span>
                  <Text strong className="text-lg">{selectedSchema.display_name}</Text>
                  <Tag color="blue" size="small">{selectedSchema.category}</Tag>
                </div>
                <Paragraph type="tertiary" className="!mb-0">{selectedSchema.description}</Paragraph>
              </Card>
            )}

            {/* Name & Description */}
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-1 mb-1.5">
                  <Text strong className="text-sm">{t("tools:config_name")}</Text>
                  <Text type="danger" className="text-sm">*</Text>
                </div>
                <Input
                  size="large"
                  value={form.name}
                  onChange={(v) => setForm((prev) => ({ ...prev, name: v }))}
                  placeholder={t("tools:config_name_placeholder")}
                  disabled={isViewMode}
                  prefix={<span className="text-gray-400">📝</span>}
                />
                {errors.name && (
                  <Text type="danger" size="small" className="mt-1">{errors.name}</Text>
                )}
              </div>

              <div>
                <Text strong className="text-sm mb-1.5 block">{t("tools:description")}</Text>
                <TextArea
                  value={form.description}
                  onChange={(v) => setForm((prev) => ({ ...prev, description: v }))}
                  placeholder={t("tools:description_placeholder")}
                  disabled={isViewMode}
                  rows={2}
                  autosize
                />
              </div>
            </div>

            {/* Config Fields */}
            {selectedSchema?.fields && selectedSchema.fields.length > 0 && (
              <>
                <Divider margin={16}>
                  <Tag color="purple" size="small">⚙️ {t("tools:configuration")}</Tag>
                </Divider>
                <Card className="!rounded-xl" bodyStyle={{ padding: 16 }}>
                  {selectedSchema.fields.map(renderConfigField)}
                </Card>
              </>
            )}

            {/* Active Toggle */}
            <Card className="!rounded-xl" bodyStyle={{ padding: 16 }}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg">⚡</span>
                    <Text strong>{t("tools:active")}</Text>
                  </div>
                  <Text type="tertiary" size="small">{t("tools:active_description")}</Text>
                </div>
                <Switch
                  checked={form.is_active}
                  onChange={(checked) => setForm((prev) => ({ ...prev, is_active: checked }))}
                  disabled={isViewMode}
                  checkedText="ON"
                  uncheckedText="OFF"
                />
              </div>
            </Card>
          </div>
        )}
      </SideSheet>

      {/* Delete Confirmation */}
      <Modal
        title={
          <div className="flex items-center gap-2 text-red-600">
            <Trash2 className="h-5 w-5" />
            {t("tools:delete_confirm_title")}
          </div>
        }
        visible={deleteConfirmOpen}
        onCancel={() => setDeleteConfirmOpen(false)}
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setDeleteConfirmOpen(false)}>{t("common:cancel")}</Button>
            <Button type="danger" theme="solid" onClick={handleDelete}>
              {t("common:delete")}
            </Button>
          </div>
        }
        width={400}
      >
        <Text type="tertiary">{t("tools:delete_confirm_description")}</Text>
      </Modal>
    </>
  );
};

export default UserToolSheet;
