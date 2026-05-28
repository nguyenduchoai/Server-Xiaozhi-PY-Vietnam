/**
 * AgentAIConfigSection - Inline AI Configuration Editor for Agent
 * Agent-Centric Architecture: Edit LLM, TTS, ASR, prompt directly on agent
 * Premium UI with glassmorphism, gradient cards, micro-animations
 */

"use client";

import React, { useState, useMemo, useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  Typography,
  Button,
  Form,
  Select,
  Toast,
  Tag,
  Collapsible,
  Banner,
  Spin,
  Popconfirm,
} from "@douyinfe/semi-ui";
import {
  IconEdit,
  IconTick,
  IconClose,
  IconCopy,
  IconRefresh,
} from "@douyinfe/semi-icons";
import { Cpu, Mic, Volume2, Brain, Zap, MessageSquare, Sparkles, FileText } from "lucide-react";

import { useUpdateAgent, useCloneTemplateToAgent } from "@/queries/agent-queries";
import { useProviderModules } from "@/hooks";
import apiClient from "@config/axios-instance";
import { PROVIDER_ENDPOINTS } from "@lib/api";
import type { Agent, Template, ProviderModuleItem } from "@types";
import type { ProviderModulesResponse } from "@/queries/provider-queries";

const { Text, Title, Paragraph } = Typography;

// ============ TTS Voice Select (Dynamic Voice Loading) ============

interface VoiceOption {
  id: string;
  name: string;
  category?: string;
}

interface TTSVoiceSelectProps {
  modules?: ProviderModulesResponse;
  ttsRef?: string;
}

const TTSVoiceSelect = ({ modules, ttsRef }: TTSVoiceSelectProps) => {
  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualMode, setManualMode] = useState(false);
  const [lastLoadedType, setLastLoadedType] = useState<string | null>(null);

  // Resolve TTS reference to provider type
  const ttsProviderType = useMemo(() => {
    if (!ttsRef || !modules?.TTS) return null;
    const ttsModule = modules.TTS.find(
      (m: ProviderModuleItem) => m.reference === ttsRef
    );
    return ttsModule?.type || null;
  }, [ttsRef, modules?.TTS]);

  // Load voices when TTS provider type changes
  const loadVoices = useCallback(async (providerType: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(
        PROVIDER_ENDPOINTS.VOICES(providerType)
      );
      const items: VoiceOption[] = response.data?.voices || [];
      setVoices(items);
      setLastLoadedType(providerType);
      if (response.data?.error && items.length === 0) {
        setError(response.data.error);
      }
    } catch (err: any) {
      setError(err?.message || "Không thể tải danh sách giọng");
      setVoices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-load when TTS type changes
  useEffect(() => {
    if (ttsProviderType && ttsProviderType !== lastLoadedType) {
      loadVoices(ttsProviderType);
    }
  }, [ttsProviderType, lastLoadedType, loadVoices]);

  // Build options for Select
  const voiceOptions = useMemo(() => {
    return voices.map((v) => ({
      value: v.id,
      label: v.name,
    }));
  }, [voices]);

  if (manualMode) {
    return (
      <div>
        <div className="flex items-center justify-between mb-1">
          <Text strong size="small">🎤 TTS Voice ID</Text>
          <Button
            size="small"
            theme="borderless"
            type="primary"
            onClick={() => setManualMode(false)}
          >
            ← Chọn từ danh sách
          </Button>
        </div>
        <Form.Input
          field="tts_voice"
          noLabel
          placeholder="VD: vi-VN-HoaiMyNeural, alloy, echo"
        />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <Text strong size="small">🎤 Giọng nói TTS</Text>
        <div className="flex gap-1">
          {ttsProviderType && (
            <Button
              size="small"
              theme="borderless"
              icon={<IconRefresh />}
              loading={loading}
              onClick={() => ttsProviderType && loadVoices(ttsProviderType)}
            >
              Load
            </Button>
          )}
          <Button
            size="small"
            theme="borderless"
            type="tertiary"
            onClick={() => setManualMode(true)}
          >
            Nhập thủ công
          </Button>
        </div>
      </div>

      {!ttsProviderType ? (
        <Form.Input
          field="tts_voice"
          noLabel
          placeholder="Chọn TTS provider trước để load giọng"
        />
      ) : voices.length > 0 ? (
        <Form.Select
          field="tts_voice"
          noLabel
          placeholder={`Chọn giọng (${voices.length} giọng có sẵn)`}
          optionList={voiceOptions}
          showClear
          filter
          loading={loading}
          style={{ width: "100%" }}
        />
      ) : (
        <div>
          <Form.Input
            field="tts_voice"
            noLabel
            placeholder={loading ? "Đang tải..." : "Bấm Load hoặc nhập voice ID"}
          />
          {error && (
            <Text type="warning" size="small" className="mt-1 block">
              ⚠️ {error}
            </Text>
          )}
        </div>
      )}
    </div>
  );
};

// ============ Provider Badge (View Mode) ============

interface ProviderDisplayProps {
  label: string;
  value?: string | null;
  displayName?: string;
  icon: React.ReactNode;
  color: string;
  /** CSS custom property key, e.g. "llm" → reads --provider-llm-bg */
  tokenKey?: string;
}

/** Extract readable name from reference like "config:OpenAI_GPT4" or "db:UUID" */
const getDisplayName = (ref?: string | null, modules?: ProviderModulesResponse): string => {
  if (!ref) return "";
  
  // Try to find the exact name from the modules registry
  if (modules) {
    for (const category of Object.values(modules)) {
      if (Array.isArray(category)) {
        const match = category.find((m: any) => m.reference === ref);
        if (match && match.name) return match.name;
      }
    }
  }

  // Fallback to stripping prefixes
  const name = ref.replace(/^(config:|db:)/, "");
  // If it looks like a clean string, space it out. If it's a UUID, just return it (better than nothing)
  if (name.length === 36 && name.split('-').length === 5) return "Custom Provider";
  return name.replace(/_/g, " ");
};

const ProviderBadge = ({ label, value, icon, color, modules, voiceName }: ProviderDisplayProps & { modules?: ProviderModulesResponse, voiceName?: string | null }) => {
  if (!value) return null;
  const displayName = getDisplayName(value, modules);
  // Use a refined dynamic background based on the explicit color for a premium glass feel
  const bgStyle = `linear-gradient(145deg, ${color}10, ${color}05)`;
  const borderColor = `${color}30`;
  const iconBgVar = `linear-gradient(135deg, ${color}20, ${color}40)`;

  return (
    <div
      className="group flex flex-col h-full gap-2 p-4 rounded-2xl transition-all duration-300 hover:scale-[1.01] hover:shadow-md cursor-default relative overflow-hidden"
      style={{
        background: bgStyle,
        border: `1px solid ${borderColor}`,
        backdropFilter: "blur(12px)",
      }}
    >
      <div className="absolute top-0 right-0 w-24 h-24 rounded-full blur-2xl opacity-20" style={{ background: color, transform: 'translate(30%, -30%)' }} />
      
      <div className="flex items-start gap-3 relative z-10">
        <div
          className="flex items-center justify-center w-11 h-11 rounded-xl shadow-sm transition-transform duration-300 group-hover:rotate-3 flex-shrink-0"
          style={{ background: iconBgVar }}
        >
          {icon}
        </div>
        <div className="flex-1 min-w-0 pt-0.5">
          <Text type="tertiary" size="small" className="block uppercase tracking-widest font-semibold" style={{ fontSize: 10, letterSpacing: '0.15em', color: color }}>
            {label}
          </Text>
          <Text strong className="block truncate text-sm mt-1" style={{ fontSize: '15px' }}>{displayName}</Text>
        </div>
        <div className="w-2 h-2 rounded-full mt-2 animate-pulse flex-shrink-0" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      </div>
      
      {voiceName && label === "TTS" && (
        <div className="mt-2 pt-2 border-t relative z-10" style={{ borderTopColor: `${color}20` }}>
          <Tag color="blue" size="small" type="ghost" className="!rounded-md" style={{ background: `${color}10`, color: color, border: 'none' }}>
            🎤 {voiceName}
          </Tag>
        </div>
      )}
    </div>
  );
};

/** Empty provider slot for unconfigured providers */
const EmptyProviderSlot = ({ label, icon, color }: { label: string; icon: React.ReactNode; color: string }) => {
  return (
    <div
      className="flex h-full items-start gap-3 p-4 rounded-2xl border border-dashed opacity-50 hover:opacity-80 transition-opacity bg-black/[0.01] dark:bg-white/[0.01]"
      style={{ borderColor: `${color}30` }}
    >
      <div className="flex items-center justify-center w-11 h-11 rounded-xl flex-shrink-0" style={{ background: `${color}10` }}>
        {React.cloneElement(icon as React.ReactElement, { opacity: 0.5 })}
      </div>
      <div className="flex-1 pt-0.5">
        <Text type="quaternary" size="small" className="block uppercase tracking-widest font-semibold" style={{ fontSize: 10, letterSpacing: '0.15em' }}>
          {label}
        </Text>
        <Text type="quaternary" className="text-sm mt-1">Chưa cấu hình</Text>
      </div>
    </div>
  );
};

// ============ Main Component ============

interface AgentAIConfigSectionProps {
  agent: Agent;
  agentId: string;
  templates?: Template[];
  onRefresh?: () => void;
}

export const AgentAIConfigSection = ({
  agent,
  agentId,
  templates,
  onRefresh,
}: AgentAIConfigSectionProps) => {
  const { t } = useTranslation("agents");
  const [isEditing, setIsEditing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);
  const [selectedTTS, setSelectedTTS] = useState<string | undefined>(agent.TTS || undefined);
  const [voiceMap, setVoiceMap] = useState<Record<string, string>>({});

  const updateAgent = useUpdateAgent();
  const cloneTemplate = useCloneTemplateToAgent(agentId);
  const { modules, isLoading: modulesLoading } = useProviderModules(true);

  // Resolve TTS provider type from modules
  const ttsProviderType = useMemo(() => {
    const ttsRef = agent.TTS;
    if (!ttsRef || !modules?.TTS) return null;
    const ttsModule = (modules.TTS as ProviderModuleItem[]).find(
      (m) => m.reference === ttsRef
    );
    return ttsModule?.type || null;
  }, [agent.TTS, modules?.TTS]);

  // Auto-load voice names for view mode
  useEffect(() => {
    if (!ttsProviderType) return;
    apiClient.get(PROVIDER_ENDPOINTS.VOICES(ttsProviderType))
      .then((res) => {
        const voices: VoiceOption[] = res.data?.voices || [];
        const map: Record<string, string> = {};
        for (const v of voices) {
          map[v.id] = v.name;
        }
        setVoiceMap(map);
      })
      .catch(() => { /* silent fallback to raw ID */ });
  }, [ttsProviderType]);

  // Resolve voice ID to friendly name
  const resolvedVoiceName = useMemo(() => {
    if (!agent.tts_voice) return null;
    return voiceMap[agent.tts_voice] || agent.tts_voice;
  }, [agent.tts_voice, voiceMap]);

  const formatOptions = useCallback(
    (category: string) => {
      const items = modules?.[category as keyof typeof modules];
      if (!Array.isArray(items)) return [];
      return items.map((m: any) => ({
        value: m.reference,
        label: `${m.name}${m.source === "default" ? " ⚙️" : m.source === "public" ? " 🌐" : ""}`,
      }));
    },
    [modules]
  );

  const llmOptions = useMemo(() => formatOptions("LLM"), [formatOptions]);
  const ttsOptions = useMemo(() => formatOptions("TTS"), [formatOptions]);
  const asrOptions = useMemo(() => formatOptions("ASR"), [formatOptions]);
  const vllmOptions = useMemo(() => formatOptions("VLLM"), [formatOptions]);
  const memoryOptions = useMemo(() => formatOptions("Memory"), [formatOptions]);
  const intentOptions = useMemo(() => formatOptions("Intent"), [formatOptions]);

  // Provider display items — using HEX values directly as fallback since CSS tokens are missing
  const providerItems = [
    { label: "LLM", value: agent.LLM, icon: <Cpu size={18} color="#6366f1" />, color: "#6366f1", tokenKey: "llm" },
    { label: "TTS", value: agent.TTS, icon: <Volume2 size={18} color="#06b6d4" />, color: "#06b6d4", tokenKey: "tts" },
    { label: "ASR", value: agent.ASR, icon: <Mic size={18} color="#f59e0b" />, color: "#f59e0b", tokenKey: "asr" },
    { label: "VLLM", value: agent.VLLM, icon: <Zap size={18} color="#8b5cf6" />, color: "#8b5cf6", tokenKey: "vllm" },
    { label: "Memory", value: agent.Memory, icon: <Brain size={18} color="#10b981" />, color: "#10b981", tokenKey: "memory" },
    { label: "Intent", value: agent.Intent, icon: <MessageSquare size={18} color="#ef4444" />, color: "#ef4444", tokenKey: "intent" },
  ];

  const configuredCount = providerItems.filter((p) => p.value).length;
  const hasAnyConfig = configuredCount > 0 || agent.prompt;

  // Handle form submit
  const handleSave = async (values: any) => {
    setIsSubmitting(true);
    try {
      const payload: any = {};
      const fields = ["prompt", "LLM", "TTS", "ASR", "VLLM", "Memory", "Intent", "tts_voice", "summary_memory"];
      for (const f of fields) {
        if (values[f] !== undefined) {
          payload[f] = values[f] || null;
        }
      }


      await updateAgent.mutateAsync({ agentId, payload });
      Toast.success({ content: t("agent_config_saved", "✅ Đã lưu cấu hình AI"), duration: 3 });
      setIsEditing(false);
      onRefresh?.();
    } catch (err: any) {
      Toast.error({ content: err?.message || "Lỗi khi lưu cấu hình", duration: 5 });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle clone from template
  const handleClone = async (templateId: string) => {
    try {
      await cloneTemplate.mutateAsync(templateId);
      Toast.success({ content: t("cloned_from_template", "✅ Đã sao chép cấu hình từ Template"), duration: 3 });
      onRefresh?.();
    } catch (err: any) {
      Toast.error({ content: err?.message || "Lỗi khi sao chép", duration: 5 });
    }
  };

  // ============ VIEW MODE ============
  if (!isEditing) {
    return (
      <div className="space-y-5 animate-fadeIn">
        {/* Header with gradient accent */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/10 to-indigo-500/20">
              <Sparkles size={20} className="text-blue-500" />
            </div>
            <div>
              <Title heading={5} className="!mb-0">
                {t("ai_configuration", "Cấu hình AI")}
              </Title>
              <Text type="tertiary" size="small">
                {configuredCount > 0
                  ? `${configuredCount}/6 providers • ${agent.prompt ? "Prompt ✓" : "No prompt"}`
                  : "Chưa cấu hình"}
              </Text>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {templates && templates.length > 0 && (
              <Popconfirm
                title="Sao chép cấu hình?"
                content="Chọn template để sao chép cấu hình AI vào agent này. Các cấu hình hiện tại sẽ bị ghi đè."
                onConfirm={() => {}}
                okText="OK"
                cancelText="Hủy"
              >
                <Select
                  placeholder={t("clone_from_template", "📋 Sao chép từ Template...")}
                  style={{ width: 230 }}
                  optionList={templates.map((tpl: any) => ({
                    value: tpl.id || tpl.template_id,
                    label: tpl.name || tpl.template_name || "Template",
                  }))}
                  onChange={(val) => val && handleClone(val as string)}
                  loading={cloneTemplate.isPending}
                  prefix={<IconCopy />}
                  size="default"
                />
              </Popconfirm>
            )}
            <Button
              icon={<IconEdit />}
              theme="solid"
              type="primary"
              onClick={() => setIsEditing(true)}
              style={{
                background: "var(--gradient-primary)",
                border: "none",
              }}
            >
              {t("edit_config", "Chỉnh sửa")}
            </Button>
          </div>
        </div>

        {!hasAnyConfig ? (
          <Banner
            type="info"
            icon={<Sparkles size={16} />}
            description={
              <span>
                Agent chưa có cấu hình AI. Nhấn{" "}
                <Text strong link onClick={() => setIsEditing(true)}>Chỉnh sửa</Text>
                {" "}hoặc sao chép từ Template để bắt đầu.
              </span>
            }
            className="!rounded-xl"
          />
        ) : (
          <div className="space-y-4">
            {/* Provider Grid — show all 6 slots */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {providerItems.map((item) =>
                item.value ? (
                  <ProviderBadge key={item.label} {...item} modules={modules} voiceName={resolvedVoiceName} />
                ) : (
                  <EmptyProviderSlot key={item.label} label={item.label} icon={item.icon} color={item.color} />
                )
              )}
            </div>

            {/* Prompt Preview — Glassmorphism card */}
            {agent.prompt && (
              <div
                className="rounded-2xl overflow-hidden transition-all duration-300"
                style={{
                  background: "var(--glass-primary)",
                  border: "1px solid var(--glass-primary-border)",
                }}
              >
                <div
                  className="flex items-center justify-between px-4 py-3 cursor-pointer select-none hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors"
                  onClick={() => setShowPrompt(!showPrompt)}
                >
                  <div className="flex items-center gap-2">
                    <MessageSquare size={14} className="text-indigo-500" />
                    <Text type="tertiary" size="small" className="uppercase tracking-wider font-semibold" style={{ fontSize: 10 }}>
                      System Prompt
                    </Text>
                  </div>
                  <div className="flex items-center gap-2">
                    <Tag size="small" color="violet" type="ghost">
                      {agent.prompt.length} chars
                    </Tag>
                    <Text type="tertiary" size="small" className="transition-transform duration-200" style={{ transform: showPrompt ? "rotate(180deg)" : "none" }}>
                      ▼
                    </Text>
                  </div>
                </div>
                <Collapsible isOpen={showPrompt}>
                  <div className="px-4 pb-4 max-h-64 overflow-auto">
                    <Paragraph className="text-sm whitespace-pre-wrap !mb-0 font-mono leading-relaxed" style={{ color: "var(--semi-color-text-0)" }}>
                      {agent.prompt}
                    </Paragraph>
                  </div>
                </Collapsible>
              </div>
            )}

            {/* Source Template Info */}
            {agent.source_template_id && (
              <Text type="tertiary" size="small" className="flex items-center gap-1.5">
                <FileText size={12} /> Nguồn: <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">{agent.source_template_id}</code>
              </Text>
            )}
          </div>
        )}
      </div>
    );
  }

  // ============ EDIT MODE ============
  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500/10 to-amber-500/20">
            <IconEdit size="large" className="text-orange-500" />
          </div>
          <div>
            <Title heading={5} className="!mb-0">
              {t("editing_ai_config", "Chỉnh sửa cấu hình AI")}
            </Title>
            <Text type="tertiary" size="small">
              Thay đổi providers, prompt và tính năng
            </Text>
          </div>
        </div>
        <Button
          icon={<IconClose />}
          theme="borderless"
          type="tertiary"
          onClick={() => setIsEditing(false)}
          disabled={isSubmitting}
        />
      </div>

      <Form
        onSubmit={handleSave}
        onValueChange={(values) => {
          if (values.TTS !== selectedTTS) setSelectedTTS(values.TTS as string | undefined);
        }}
        initValues={{
          prompt: agent.prompt || "",
          LLM: agent.LLM || undefined,
          TTS: agent.TTS || undefined,
          ASR: agent.ASR || undefined,
          VLLM: agent.VLLM || undefined,
          Memory: agent.Memory || undefined,
          Intent: agent.Intent || undefined,
          tts_voice: agent.tts_voice || "",
          summary_memory: agent.summary_memory || "",
        }}
        labelPosition="top"
        className="space-y-4"
      >
        {/* System Prompt — First so users write prompt before selecting providers */}
        <Card
          className="!rounded-2xl"
          title={
            <div className="flex items-center gap-2">
              <MessageSquare size={16} className="text-green-500" />
              <Text strong>System Prompt</Text>
            </div>
          }
          headerStyle={{ borderBottom: "1px solid var(--apple-border-primary)" }}
        >
          <Form.TextArea
            field="prompt"
            label="Prompt chính"
            placeholder="Bạn là trợ lý AI thông minh, thân thiện và hữu ích..."
            autosize={{ minRows: 5, maxRows: 15 }}
          />
          <Form.TextArea
            field="summary_memory"
            label="Summary Memory"
            placeholder="Tóm tắt ngữ cảnh hội thoại (tự động bởi Memory provider)"
            autosize={{ minRows: 2, maxRows: 6 }}
            className="mt-4"
          />
        </Card>

        {/* Provider Selectors */}
        <Card
          className="!rounded-2xl"
          title={
            <div className="flex items-center gap-2">
              <Cpu size={16} className="text-indigo-500" />
              <Text strong>AI Providers</Text>
              {modulesLoading && <Spin size="small" />}
            </div>
          }
          headerStyle={{ borderBottom: "1px solid var(--apple-border-primary)" }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Form.Select field="LLM" label="🧠 LLM (Mô hình ngôn ngữ)" placeholder="Chọn LLM..." optionList={llmOptions} showClear filter style={{ width: "100%" }} />
            <Form.Select field="TTS" label="🔊 TTS (Text-to-Speech)" placeholder="Chọn TTS..." optionList={ttsOptions} showClear filter style={{ width: "100%" }} />
            <Form.Select field="ASR" label="🎙️ ASR (Speech-to-Text)" placeholder="Chọn ASR..." optionList={asrOptions} showClear filter style={{ width: "100%" }} />
            <Form.Select field="VLLM" label="👁️ VLLM (Vision LLM)" placeholder="Chọn VLLM..." optionList={vllmOptions} showClear filter style={{ width: "100%" }} />
            <Form.Select field="Memory" label="💡 Memory" placeholder="Chọn Memory..." optionList={memoryOptions} showClear filter style={{ width: "100%" }} />
            <Form.Select field="Intent" label="🎯 Intent" placeholder="Chọn Intent..." optionList={intentOptions} showClear filter style={{ width: "100%" }} />
          </div>
          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
            <TTSVoiceSelect modules={modules} ttsRef={selectedTTS} />
          </div>
        </Card>



        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2 pb-1">
          <Button
            icon={<IconClose />}
            theme="borderless"
            onClick={() => setIsEditing(false)}
            disabled={isSubmitting}
            size="large"
          >
            {t("cancel", "Hủy")}
          </Button>
          <Button
            icon={<IconTick />}
            theme="solid"
            type="primary"
            htmlType="submit"
            loading={isSubmitting}
            size="large"
            style={{
              background: "var(--gradient-primary)",
              border: "none",
              padding: "0 24px",
            }}
          >
            {t("save_config", "Lưu cấu hình")}
          </Button>
        </div>
      </Form>
    </div>
  );
};

export default AgentAIConfigSection;
