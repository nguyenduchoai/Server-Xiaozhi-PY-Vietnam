
"use client";

import { useState, useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import type { AgentTemplate, AgentTemplateDetail, Template } from "@/types";
import { Modal, Form, Row, Col, Typography, Button as SemiButton } from '@douyinfe/semi-ui';
import { IconImport } from "@douyinfe/semi-icons";
import { apiClient } from "@/config/axios-instance"; // Use correct config path
import { SelectTemplateDialog } from "./SelectTemplateDialog";

/**
 * Provider Module Option - matches API response from /providers/config/modules
 * Uses reference format: config:{name} or db:{uuid}
 */
interface ModuleOption {
  reference: string;
  id?: string;
  name: string;
  type?: string;
  source?: "default" | "user" | "public";
}

/**
 * TTS Voice option for dropdown
 */
interface VoiceOption {
  value: string;
  label: string;
}

/**
 * Voice options mapping by TTS provider type
 * Maps TTS provider type to available voice options
 */
const TTS_VOICE_OPTIONS: Record<string, VoiceOption[]> = {
  // Valtec TTS - key matches type from config.yml
  valtec: [
    { value: "female", label: "👩 Nữ (female)" },
    { value: "male", label: "👨 Nam (male)" },
  ],

  // Edge TTS
  edge: [
    { value: "vi-VN-HoaiMyNeural", label: "Hoài My (Nữ - Việt Nam)" },
    { value: "vi-VN-NamMinhNeural", label: "Nam Minh (Nam - Việt Nam)" },
    { value: "en-US-JennyNeural", label: "Jenny (Nữ - US)" },
    { value: "en-US-GuyNeural", label: "Guy (Nam - US)" },
    { value: "en-GB-SoniaNeural", label: "Sonia (Nữ - UK)" },
    { value: "ja-JP-NanamiNeural", label: "Nanami (Nữ - Japan)" },
    { value: "zh-CN-XiaoxiaoNeural", label: "Xiaoxiao (Nữ - China)" },
  ],
};

interface CreateTemplateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  template?: AgentTemplate | AgentTemplateDetail | null;
  onSubmit: (data: any) => Promise<void>;
  isLoading?: boolean;
  initialValues?: any;
  modules?: {
    ASR?: ModuleOption[];
    TTS?: ModuleOption[];
    LLM?: ModuleOption[];
    VLLM?: ModuleOption[];
    Memory?: ModuleOption[];
    Intent?: ModuleOption[];
  };
  modulesLoading?: boolean;
}

export function CreateTemplateDialog({
  open,
  onOpenChange,
  template,
  initialValues,
  onSubmit,
  isLoading = false,
  modules,
  modulesLoading = false,
}: CreateTemplateDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { t } = useTranslation("agents");
  const [formApi, setFormApi] = useState<any>();
  const [showLibrary, setShowLibrary] = useState(false);
  const [loadingTemplate, setLoadingTemplate] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);

  /**
   * Extract provider reference from provider field
   * Handles both string (reference) and object (ProviderInfo) formats
   * Returns reference string for form value
   */
  const getProviderReference = (
    provider: string | { reference?: string; id?: string } | undefined | null
  ): string => {
    if (!provider) return "";
    if (typeof provider === "string") return provider;
    return provider.reference || provider.id || "";
  };

  const {
    watch,
    setValue,
    reset,
  } = useForm({
    defaultValues: {
      name: "",
      prompt: "",
      ASR: "",
      TTS: "",
      tts_voice: "",
      LLM: "",
      VLLM: "",
      Memory: "",
      Intent: "",
      summary_memory: "",
      enable_memory: true,
      enable_knowledge_base: true,
      knowledge_base_ids: [] as string[],
    },
  });

  // Watch TTS value to show relevant voice options
  const selectedTTS = watch("TTS");
  const selectedVoice = watch("tts_voice");

  const handleSelectFromLibrary = async (templateId: string) => {
    try {
      setLoadingTemplate(true);
      setShowLibrary(false);

      const { data } = await apiClient.get<Template>(`/api/v1/templates/${templateId}`);

      if (data) {
        const formValues = {
          name: `${data.name} (Copy)`,
          prompt: data.prompt,
          ASR: getProviderReference(data.ASR),
          LLM: getProviderReference(data.LLM),
          VLLM: getProviderReference(data.VLLM),
          TTS: getProviderReference(data.TTS),
          tts_voice: data.tts_voice || "",
          Memory: getProviderReference(data.Memory),
          Intent: getProviderReference(data.Intent),
          summary_memory: data.summary_memory || "",
          enable_memory: data.enable_memory ?? true,
          enable_knowledge_base: data.enable_knowledge_base ?? true,
        };
        reset(formValues); // Use react-hook-form's reset
        if (formApi) {
          formApi.setValues(formValues); // Also update Semi UI form's internal state
        }
      }
    } catch (e) {
      console.error("Failed to load template", e);
    } finally {
      setLoadingTemplate(false);
    }
  };

  // Sync form api with react hook form
  useEffect(() => {
    if (formApi) {
      if (template) {
        const values = {
          name: template.name || "",
          prompt: template.prompt || "",
          ASR: getProviderReference(template.ASR),
          TTS: getProviderReference(template.TTS),
          tts_voice: template.tts_voice || "",
          LLM: getProviderReference(template.LLM),
          VLLM: getProviderReference(template.VLLM),
          Memory: getProviderReference(template.Memory),
          Intent: getProviderReference(template.Intent),
          summary_memory: template.summary_memory || "",
          enable_memory: template.enable_memory ?? true,
          enable_knowledge_base: template.enable_knowledge_base ?? true,
          knowledge_base_ids: [],
        };
        formApi.setValues(values);
        reset(values);
        // Set KB IDs from template (if available)
        if ((template as any).knowledge_base_ids) {
          setSelectedKbIds((template as any).knowledge_base_ids);
        }
        // Mark initial load complete after a tick to allow watchers to stabilize
        setTimeout(() => setIsInitialLoad(false), 100);
      } else if (initialValues) {
        formApi.setValues(initialValues);
        reset(initialValues);
        if (initialValues.knowledge_base_ids) {
          setSelectedKbIds(initialValues.knowledge_base_ids);
        }
      } else {
        const defaults = {
          name: "",
          prompt: "",
          ASR: "",
          TTS: "",
          tts_voice: "",
          LLM: "",
          VLLM: "",
          Memory: "",
          Intent: "",
          summary_memory: "",
          enable_memory: true,
          enable_knowledge_base: true,
          knowledge_base_ids: [],
        };
        if (!open) {
          formApi.setValues(defaults);
          reset(defaults);
          setSelectedKbIds([]);
          setIsInitialLoad(true);
        }
      }
    }
  }, [template, initialValues, formApi, open, reset]);


  /**
   * Get TTS provider type from reference
   * Extracts type from modules list or reference format
   */
  const getSelectedTTSType = useMemo(() => {
    if (!selectedTTS) return null;

    // Find matching module to get type
    const ttsModule = modules?.TTS?.find(m => m.reference === selectedTTS);
    if (ttsModule?.type) {
      return ttsModule.type.toLowerCase();
    }

    // Fallback: try to extract from reference name
    const refName = selectedTTS.replace("config:", "").replace("db:", "").toLowerCase();
    // NghiTTS detection (legacy)
    if (refName.includes("nghitts") || refName.includes("nghi")) return "nghitts";
    if (refName.includes("valtec")) return "valtec";

    if (refName.includes("edge")) return "edge";

    return null;
  }, [selectedTTS, modules?.TTS]);

  // Get voice options for current TTS type
  const voiceOptions = useMemo(() => {
    if (!getSelectedTTSType) return [];
    return TTS_VOICE_OPTIONS[getSelectedTTSType] || [];
  }, [getSelectedTTSType]);

  // Clear voice when TTS changes (but not during initial form load)
  useEffect(() => {
    // Skip during initial load to preserve saved tts_voice value
    if (isInitialLoad) return;

    // Only clear if voice is not in new options
    if (selectedVoice && voiceOptions.length > 0) {
      const isValidVoice = voiceOptions.some(v => v.value === selectedVoice);
      if (!isValidVoice) {
        if (formApi) formApi.setValue("tts_voice", "");
        setValue("tts_voice", "");
      }
    }
  }, [selectedTTS, voiceOptions, selectedVoice, setValue, formApi, isInitialLoad]);


  const onSubmitHandler = async (data: any) => {
    setIsSubmitting(true);
    try {
      const payload: any = {
        name: data.name,
        prompt: data.prompt,
        summary_memory: data.summary_memory || null,
        ASR: data.ASR || null,
        LLM: data.LLM || null,
        VLLM: data.VLLM || null,
        TTS: data.TTS || null,
        tts_voice: data.tts_voice || null,
        Memory: data.Memory || null,
        Intent: data.Intent || null,
        enable_memory: data.enable_memory ?? true,
        enable_knowledge_base: data.enable_knowledge_base ?? true,
        knowledge_base_ids: selectedKbIds.length > 0 ? selectedKbIds : null,
      };

      await onSubmit(payload);
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isSubmittingForm = isSubmitting || isLoading;

  const formatOptions = (options?: ModuleOption[]) => {
    return [
      { value: "", label: t("use_server_default") },
      ...(options || []).map(opt => ({
        value: opt.reference,
        // Both 'default' and 'public' show as "Mặc Định"
        label: `${opt.name} (${opt.source === 'default' || opt.source === 'public' ? t("default") : t("custom")})`
      }))
    ];
  }

  const handleFormChange = (formState: any) => {
    const values = formState.values;
    // Sync with react-hook-form needed for watchers
    if (values.TTS !== selectedTTS) setValue("TTS", values.TTS);
    if (values.tts_voice !== selectedVoice) setValue("tts_voice", values.tts_voice);
  }

  return (
    <>
      <Modal
        title={template ? t("edit_template") : t("create_template")}
        visible={open}
        onCancel={() => onOpenChange(false)}
        onOk={() => formApi?.submitForm()}
        confirmLoading={isSubmittingForm}
        okText={template ? t("update_template") : t("create_template")}
        cancelText={t("cancel")}
        size="large"
        style={{ width: 900 }}
      >
        <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            {template ? t("update_template_desc") : t("create_template_desc")}
          </div>
          {!template && (
            <SemiButton
              icon={<IconImport />}
              onClick={() => setShowLibrary(true)}
              theme="light"
              type="primary"
            >
              {t("select_from_library", "Chọn từ thư viện")}
            </SemiButton>
          )}
        </div>

        <Form
          getFormApi={setFormApi}
          onSubmit={onSubmitHandler}
          onChange={handleFormChange}
          labelPosition="top"
        >
          <Row gutter={16}>
            <Col span={24}>
              <Form.Input
                field="name"
                label={t("template_name") + " *"}
                placeholder={t("enter_template_name")}
                rules={[{ required: true, message: t("template_name_required") }]}
                disabled={isSubmittingForm}
              />
            </Col>
            <Col span={24}>
              <Form.TextArea
                field="prompt"
                label={t("prompt") + " *"}
                placeholder={t("enter_system_prompt")}
                rules={[{ required: true, message: t("prompt_required") }]}
                rows={6}
                disabled={isSubmittingForm}
              />
            </Col>
          </Row>

          <Typography.Title heading={6} style={{ marginTop: 16, marginBottom: 8 }}>Modules</Typography.Title>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Select
                field="ASR"
                label="ASR"
                optionList={formatOptions(modules?.ASR)}
                disabled={modulesLoading || isSubmittingForm}
                style={{ width: '100%' }}
                placeholder={t("use_server_default")}
              />
            </Col>
            <Col span={8}>
              <Form.Select
                field="LLM"
                label="LLM"
                optionList={formatOptions(modules?.LLM)}
                disabled={modulesLoading || isSubmittingForm}
                style={{ width: '100%' }}
                placeholder={t("use_server_default")}
              />
            </Col>
            <Col span={8}>
              <Form.Select
                field="VLLM"
                label="VLLM"
                optionList={formatOptions(modules?.VLLM)}
                disabled={modulesLoading || isSubmittingForm}
                style={{ width: '100%' }}
                placeholder={t("use_server_default")}
              />
            </Col>
          </Row>

          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={8}>
              <Form.Select
                field="TTS"
                label="TTS"
                optionList={formatOptions(modules?.TTS)}
                disabled={modulesLoading || isSubmittingForm}
                style={{ width: '100%' }}
                placeholder={t("use_server_default")}
              />
            </Col>
            {selectedTTS && voiceOptions.length > 0 && (
              <Col span={8}>
                <Form.Select
                  field="tts_voice"
                  label={t("tts_voice", "Giọng nói")}
                  optionList={[
                    { value: "", label: t("use_provider_default", "Sử dụng mặc định của Provider") },
                    ...voiceOptions
                  ]}
                  disabled={isSubmittingForm}
                  style={{ width: '100%' }}
                  helpText={t("tts_voice_hint", "Chọn giọng nói cho TTS này")}
                />
              </Col>
            )}
          </Row>

          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={8}>
              <Form.Select
                field="Memory"
                label="Memory"
                optionList={formatOptions(modules?.Memory)}
                disabled={modulesLoading || isSubmittingForm}
                style={{ width: '100%' }}
                placeholder={t("use_server_default")}
              />
            </Col>
            <Col span={8}>
              <Form.Select
                field="Intent"
                label="Intent"
                optionList={formatOptions(modules?.Intent)}
                disabled={modulesLoading || isSubmittingForm}
                style={{ width: '100%' }}
                placeholder={t("use_server_default")}
              />
            </Col>
          </Row>

          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={24}>
              <Form.Input
                field="summary_memory"
                label="Summary Memory"
                placeholder="Enter summary memory"
                disabled={isSubmittingForm}
              />
            </Col>
          </Row>

          <Typography.Title heading={6} style={{ marginTop: 16, marginBottom: 8 }}>
            🧠 Knowledge & Memory
          </Typography.Title>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Switch
                field="enable_memory"
                label={t("enable_memory", "Bộ Nhớ Cá Nhân")}
                initValue={true}
                disabled={isSubmittingForm}
                extraText={t("enable_memory_desc", "Nhớ thông tin cá nhân như tên, sở thích")}
              />
            </Col>
            <Col span={12}>
              <Form.Switch
                field="enable_knowledge_base"
                label={t("enable_knowledge_base", "Kho Tri Thức")}
                initValue={true}
                disabled={isSubmittingForm}
                extraText={t("enable_knowledge_base_desc", "Sử dụng dữ liệu đã upload (PDF, Excel)")}
              />
            </Col>
          </Row>

          {/* Knowledge Base Selection */}
          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={24}>
              <div style={{ marginBottom: 4 }}>
                <Typography.Text strong>
                  {t("select_knowledge_bases", "Chọn Kho Tri Thức")}
                </Typography.Text>
              </div>
              <Typography.Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 8 }}>
                {t("select_knowledge_bases_desc", "Template này sẽ tìm kiếm trong các kho tri thức được chọn. Để trống = sử dụng tất cả kho tri thức của agent.")}
              </Typography.Text>
              <Form.TagInput
                field="knowledge_base_ids"
                placeholder={t("enter_kb_ids", "Nhập ID kho tri thức (Enter để thêm)")}
                disabled={isSubmittingForm}
                style={{ width: '100%' }}
                onChange={(value: string[]) => setSelectedKbIds(value || [])}
                initValue={selectedKbIds}
              />
            </Col>
          </Row>

        </Form>
      </Modal>

      <SelectTemplateDialog
        open={showLibrary}
        onOpenChange={setShowLibrary}
        onSelect={handleSelectFromLibrary}
        isLoading={loadingTemplate}
      />
    </>
  );
}
