"use client";

/**
 * TemplateEditPage - Dedicated page for editing template configuration
 * Replaces the popup dialog for a better editing experience
 * Includes KB selection section
 */

import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
    Button,
    Card,
    Typography,
    Form,
    Row,
    Col,
    Skeleton,
    Banner,
    Toast,
    Spin,
    Tag,
    Checkbox,
    Empty,
} from "@douyinfe/semi-ui";
import {
    IconArrowLeft,
    IconSave,
    IconRefresh,
    IconPlus,
    IconLink,
} from "@douyinfe/semi-icons";
import { AlertCircle, Database, BookOpen } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import {
    useTemplateDetail,
    useUpdateTemplate,
} from "@/queries/template-queries";
import {
    useKnowledgeBases,
    type KnowledgeBase,
} from "@/queries/knowledge-bases-queries";
import { useProviderModules } from "@/hooks";
import { PageHead } from "@/components";
import apiClient from "@/config/axios-instance";
import type { UpdateTemplatePayload } from "@/types";

const { Title, Text, Paragraph } = Typography;

// ============================================================================
// Types
// ============================================================================

interface ModuleOption {
    reference: string;
    id?: string;
    name: string;
    type?: string;
    source?: "default" | "user" | "public";
}

interface VoiceOption {
    value: string;
    label: string;
}

// Voice options by TTS type
const TTS_VOICE_OPTIONS: Record<string, VoiceOption[]> = {
    valtec: [
        { value: "female", label: "👩 Nữ (female)" },
        { value: "male", label: "👨 Nam (male)" },
    ],
    edge: [
        { value: "vi-VN-HoaiMyNeural", label: "Hoài My (Nữ - Việt Nam)" },
        { value: "vi-VN-NamMinhNeural", label: "Nam Minh (Nam - Việt Nam)" },
        { value: "en-US-JennyNeural", label: "Jenny (Nữ - US)" },
        { value: "en-US-GuyNeural", label: "Guy (Nam - US)" },
    ],
};

// ============================================================================
// Component
// ============================================================================

export const TemplateEditPage = () => {
    const { templateId } = useParams<{ templateId: string }>();
    const navigate = useNavigate();
    const { t } = useTranslation(["templates", "common"]);

    // Form API ref
    const [formApi, setFormApi] = useState<any>();
    const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);


    // Data queries
    const { modules, isLoading: modulesLoading } = useProviderModules(true);
    const { data: kbData, isLoading: kbLoading } = useKnowledgeBases();

    const {
        data: template,
        isLoading,
        error,
        refetch,
    } = useTemplateDetail(templateId || "");

    const { mutateAsync: updateTemplate, isPending: isUpdating } =
        useUpdateTemplate();

    // Initialize form with template data
    useEffect(() => {
        if (template && formApi) {
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
                memory_scope: (template as any).memory_scope || 'agent_shared',
            };
            formApi.setValues(values);

            // Set KB IDs
            if ((template as any).knowledge_base_ids) {
                setSelectedKbIds((template as any).knowledge_base_ids);
            }

        }
    }, [template, formApi]);

    // Helper: Extract provider reference
    const getProviderReference = (
        provider: string | { reference?: string; id?: string } | undefined | null
    ): string => {
        if (!provider) return "";
        if (typeof provider === "string") return provider;
        return provider.reference || provider.id || "";
    };

    // Get selected TTS type for voice options
    const selectedTTS = formApi?.getValue?.("TTS") || "";

    const getSelectedTTSType = useMemo(() => {
        if (!selectedTTS) return null;
        const ttsModule = modules?.TTS?.find(
            (m: ModuleOption) => m.reference === selectedTTS
        );
        if (ttsModule?.type) {
            return ttsModule.type.toLowerCase();
        }
        // Fallback detection
        const refName = selectedTTS.replace("config:", "").replace("db:", "").toLowerCase();
        if (refName.includes("valtec")) return "valtec";
        if (refName.includes("edge")) return "edge";
        return null;
    }, [selectedTTS, modules?.TTS]);

    const voiceOptions = useMemo(() => {
        if (!getSelectedTTSType) return [];
        return TTS_VOICE_OPTIONS[getSelectedTTSType] || [];
    }, [getSelectedTTSType]);

    // Form submit
    const handleSubmit = async (data: any) => {
        if (!templateId) return;

        try {
            const payload: UpdateTemplatePayload = {
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
                memory_scope: data.memory_scope || 'agent_shared',
                knowledge_base_ids: selectedKbIds.length > 0 ? selectedKbIds : null,
            };

            await updateTemplate({ templateId, payload });
            Toast.success(t("templates:template_updated"));
            navigate(`/templates/${templateId}`);
        } catch (error) {
            console.error("Update template error:", error);
            Toast.error(t("templates:update_error"));
        }
    };

    // Format options for Select
    const formatOptions = (options?: ModuleOption[]) => {
        return [
            { value: "", label: t("templates:use_server_default") },
            ...(options || []).map((opt) => ({
                value: opt.reference,
                label: `${opt.name} (${opt.source === "default" || opt.source === "public"
                    ? t("templates:default")
                    : t("templates:custom")
                    })`,
            })),
        ];
    };

    // Handle KB selection toggle
    const handleKbToggle = (kbId: string, checked: boolean) => {
        if (checked) {
            // Prevent duplicates
            setSelectedKbIds((prev) => prev.includes(kbId) ? prev : [...prev, kbId]);
        } else {
            setSelectedKbIds((prev) => prev.filter((id) => id !== kbId));
        }
    };


    // ============================================================================
    // Loading & Error States
    // ============================================================================

    if (!templateId) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
                <Empty
                    title={t("templates:invalid_template_id")}
                    description={t("templates:template_id_missing")}
                >
                    <Button onClick={() => navigate("/templates")} theme="solid">
                        {t("templates:back_to_templates")}
                    </Button>
                </Empty>
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton.Title className="mb-4 w-64" />
                <Skeleton.Paragraph rows={3} className="mb-4" />
                <Skeleton.Image className="h-64 mb-4" />
                <Skeleton.Image className="h-48" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <Banner
                    type="danger"
                    description={
                        <div className="flex items-center justify-between">
                            <span>{t("templates:error_loading")}</span>
                            <Button
                                theme="borderless"
                                type="primary"
                                onClick={() => refetch()}
                            >
                                {t("common:retry")}
                            </Button>
                        </div>
                    }
                    icon={<AlertCircle />}
                />
            </div>
        );
    }

    if (!template) {
        return (
            <div className="p-6 flex items-center justify-center min-h-[400px]">
                <Empty
                    title={t("templates:template_not_found")}
                    description={t("templates:template_not_found_desc")}
                />
            </div>
        );
    }

    // ============================================================================
    // Render
    // ============================================================================

    return (
        <>
            <PageHead
                title={`${t("templates:edit_template")}: ${template.name}`}
                description="templates:page.edit_description"
                translateDescription
            />

            <div className="p-6 space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            icon={<IconArrowLeft />}
                            theme="borderless"
                            onClick={() => navigate(`/templates/${templateId}`)}
                        />
                        <div>
                            <Title heading={4} className="!mb-0">
                                {t("templates:edit_template")}
                            </Title>
                            <Text type="tertiary">{template.name}</Text>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <Button
                            icon={<IconRefresh />}
                            theme="light"
                            onClick={() => refetch()}
                        >
                            {t("common:refresh")}
                        </Button>
                        <Button
                            icon={<IconSave />}
                            theme="solid"
                            type="primary"
                            loading={isUpdating}
                            onClick={() => formApi?.submitForm()}
                        >
                            {t("common:save")}
                        </Button>
                    </div>
                </div>

                {/* Main Form */}
                <Form
                    getFormApi={setFormApi}
                    onSubmit={handleSubmit}
                    labelPosition="top"
                >
                    {/* Basic Info */}
                    <Card title={t("templates:basic_info")} className="mb-4">
                        <Row gutter={16}>
                            <Col span={24}>
                                <Form.Input
                                    field="name"
                                    label={`${t("templates:template_name")} *`}
                                    placeholder={t("templates:enter_template_name")}
                                    rules={[
                                        { required: true, message: t("templates:template_name_required") },
                                    ]}
                                />
                            </Col>
                            <Col span={24}>
                                <Form.TextArea
                                    field="prompt"
                                    label={`${t("templates:prompt")} *`}
                                    placeholder={t("templates:enter_system_prompt")}
                                    rules={[{ required: true, message: t("templates:prompt_required") }]}
                                    rows={6}
                                />
                            </Col>
                        </Row>
                    </Card>

                    {/* Provider Modules */}
                    <Card title={t("templates:modules")} className="mb-4">
                        <Spin spinning={modulesLoading}>
                            <Row gutter={16}>
                                <Col span={8}>
                                    <Form.Select
                                        field="ASR"
                                        label="ASR"
                                        optionList={formatOptions(modules?.ASR)}
                                        style={{ width: "100%" }}
                                        placeholder={t("templates:use_server_default")}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Form.Select
                                        field="LLM"
                                        label="LLM"
                                        optionList={formatOptions(modules?.LLM)}
                                        style={{ width: "100%" }}
                                        placeholder={t("templates:use_server_default")}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Form.Select
                                        field="VLLM"
                                        label="VLLM"
                                        optionList={formatOptions(modules?.VLLM)}
                                        style={{ width: "100%" }}
                                        placeholder={t("templates:use_server_default")}
                                    />
                                </Col>
                            </Row>

                            <Row gutter={16} style={{ marginTop: 12 }}>
                                <Col span={8}>
                                    <Form.Select
                                        field="TTS"
                                        label="TTS"
                                        optionList={formatOptions(modules?.TTS)}
                                        style={{ width: "100%" }}
                                        placeholder={t("templates:use_server_default")}
                                    />
                                </Col>
                                {voiceOptions.length > 0 && (
                                    <Col span={8}>
                                        <Form.Select
                                            field="tts_voice"
                                            label={t("templates:tts_voice")}
                                            optionList={[
                                                { value: "", label: t("templates:use_provider_default") },
                                                ...voiceOptions,
                                            ]}
                                            style={{ width: "100%" }}
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
                                        style={{ width: "100%" }}
                                        placeholder={t("templates:use_server_default")}
                                    />
                                </Col>
                                <Col span={8}>
                                    <Form.Select
                                        field="Intent"
                                        label="Intent"
                                        optionList={formatOptions(modules?.Intent)}
                                        style={{ width: "100%" }}
                                        placeholder={t("templates:use_server_default")}
                                    />
                                </Col>
                            </Row>

                            <Row gutter={16} style={{ marginTop: 12 }}>
                                <Col span={24}>
                                    <Form.Input
                                        field="summary_memory"
                                        label="Summary Memory"
                                        placeholder="Enter summary memory"
                                    />
                                </Col>
                            </Row>
                        </Spin>
                    </Card>

                    {/* Knowledge & Memory Settings */}
                    <Card
                        title={
                            <div className="flex items-center gap-2">
                                <span>🧠 {t("templates:knowledge_memory")}</span>
                            </div>
                        }
                        className="mb-4"
                    >
                        <Row gutter={16}>
                            <Col span={8}>
                                <Form.Switch
                                    field="enable_memory"
                                    label={t("templates:enable_memory")}
                                    extraText={t("templates:enable_memory_desc")}
                                />
                            </Col>
                            <Col span={8}>
                                <Form.Switch
                                    field="enable_knowledge_base"
                                    label={t("templates:enable_knowledge_base")}
                                    extraText={t("templates:enable_knowledge_base_desc")}
                                />
                            </Col>
                        </Row>

                        <Row gutter={16} style={{ marginTop: 16 }}>
                            <Col span={24}>
                                <Form.RadioGroup
                                    field="memory_scope"
                                    label="🧠 Memory Scope"
                                    extraText="Cách quản lý bộ nhớ khi nhiều thiết bị dùng chung agent"
                                    type="button"
                                    options={[
                                        { value: 'agent_shared', label: '🔗 Chia sẻ' },
                                        { value: 'device_isolated', label: '📱 Tách biệt' },
                                        { value: 'hybrid', label: '⚡ Lai' },
                                    ]}
                                />
                            </Col>
                        </Row>
                    </Card>
                </Form>

                {/* Knowledge Base Selection Section */}
                <Card
                    title={
                        <div className="flex items-center gap-2">
                            <Database size={18} />
                            <span>{t("templates:select_knowledge_bases")}</span>
                        </div>
                    }
                    headerExtraContent={
                        <Text type="tertiary">
                            {selectedKbIds.length} {t("templates:selected")}
                        </Text>
                    }
                >
                    <Paragraph type="tertiary" style={{ marginBottom: 16 }}>
                        {t("templates:select_knowledge_bases_desc")}
                    </Paragraph>

                    {kbLoading ? (
                        <Skeleton.Paragraph rows={3} />
                    ) : !kbData?.items || kbData.items.length === 0 ? (
                        <Empty
                            image={<Database size={48} className="text-gray-300" />}
                            title={t("templates:no_knowledge_bases")}
                            description={t("templates:no_knowledge_bases_desc")}
                        >
                            <Button
                                icon={<IconPlus />}
                                onClick={() => navigate("/knowledge")}
                            >
                                {t("templates:create_knowledge_base")}
                            </Button>
                        </Empty>
                    ) : (
                        <div className="space-y-2">
                            {kbData.items.map((kb: KnowledgeBase) => (
                                <div
                                    key={kb.id}
                                    className={`p-3 rounded-lg border transition-colors cursor-pointer ${selectedKbIds.includes(kb.id)
                                        ? "border-blue-500 bg-blue-50"
                                        : "border-gray-200 hover:border-gray-300"
                                        }`}
                                    onClick={() =>
                                        handleKbToggle(kb.id, !selectedKbIds.includes(kb.id))
                                    }
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <Checkbox
                                                checked={selectedKbIds.includes(kb.id)}
                                                onChange={(e) =>
                                                    handleKbToggle(kb.id, e.target.checked ?? false)
                                                }
                                            />
                                            <div>
                                                <Text strong>{kb.name}</Text>
                                                {kb.description && (
                                                    <Text
                                                        type="tertiary"
                                                        size="small"
                                                        className="block"
                                                    >
                                                        {kb.description}
                                                    </Text>
                                                )}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Tag color="blue" size="small">
                                                {kb.entry_count} {t("templates:entries")}
                                            </Tag>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </Card>


            </div>
        </>
    );
};
