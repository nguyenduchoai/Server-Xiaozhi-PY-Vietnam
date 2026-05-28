/**
 * OnboardingWizard - Step-by-step guide for new users
 * 
 * Shows a floating wizard overlay when user has no agents AND no devices.
 * Guides them through:
 *   Step 1: Create first AI Agent
 *   Step 2: Connect first Device
 *   Step 3: Done — redirect to Dashboard
 */

import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, Typography, Progress } from "@douyinfe/semi-ui";
import {
    Bot,
    Smartphone,
    Sparkles,
    ArrowRight,
    X,
    CheckCircle2,
    Rocket,
    Zap,
} from "lucide-react";
import { useAgentList } from "@/hooks/useAgent";
import { useDeviceList } from "@/hooks/useDevice";

const { Title, Text } = Typography;

// ============================================================================
// TYPES
// ============================================================================

interface OnboardingStep {
    id: string;
    title: string;
    subtitle: string;
    description: string;
    icon: React.ReactNode;
    actionLabel: string;
    actionRoute: string;
    checkComplete: () => boolean;
    gradient: string;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function OnboardingWizard() {
    const navigate = useNavigate();
    const { } = useTranslation();

    // Data queries — check if user has created agents/devices
    const { data: agentData, isLoading: agentsLoading } = useAgentList();
    const { data: deviceData, isLoading: devicesLoading } = useDeviceList({ page: 1, page_size: 1 });

    const [dismissed, setDismissed] = useState(() =>
        localStorage.getItem("onboarding_dismissed") === "true"
    );
    const [currentStep, setCurrentStep] = useState(0);
    const [isMinimized, setIsMinimized] = useState(false);

    const hasAgents = (agentData?.data?.length ?? 0) > 0;
    const hasDevices = (deviceData?.data?.length ?? 0) > 0;

    // Define steps
    const steps: OnboardingStep[] = useMemo(() => [
        {
            id: "create-agent",
            title: "Tạo AI Agent đầu tiên",
            subtitle: "Bước 1/3",
            description: "AI Agent là \"bộ não\" điều khiển thiết bị của bạn. Mỗi Agent có thể được cấu hình giọng nói, tính cách và kỹ năng riêng.",
            icon: <Bot size={28} />,
            actionLabel: "Tạo Agent ngay",
            actionRoute: "/agents",
            checkComplete: () => hasAgents,
            gradient: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
        },
        {
            id: "add-device",
            title: "Kết nối Thiết bị",
            subtitle: "Bước 2/3",
            description: "Kết nối thiết bị ESP32 phần cứng để Agent có thể giao tiếp với bạn qua giọng nói. Bạn cần mã kích hoạt từ thiết bị.",
            icon: <Smartphone size={28} />,
            actionLabel: "Thêm Thiết bị",
            actionRoute: "/devices",
            checkComplete: () => hasDevices,
            gradient: "linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)",
        },
        {
            id: "complete",
            title: "Hoàn tất! 🎉",
            subtitle: "Bước 3/3",
            description: "Tuyệt vời! Bạn đã sẵn sàng sử dụng Xiaozhi AI. Hãy khám phá Dashboard để quản lý mọi thứ.",
            icon: <Sparkles size={28} />,
            actionLabel: "Đi tới Dashboard",
            actionRoute: "/dashboard",
            checkComplete: () => hasAgents && hasDevices,
            gradient: "linear-gradient(135deg, #10b981 0%, #34d399 100%)",
        },
    ], [hasAgents, hasDevices]);

    // Auto-advance step based on completion
    useEffect(() => {
        if (hasAgents && currentStep === 0) setCurrentStep(1);
        if (hasDevices && currentStep === 1) setCurrentStep(2);
    }, [hasAgents, hasDevices, currentStep]);

    // Calculate progress
    const completedCount = steps.filter(s => s.checkComplete()).length;
    const progressPercent = Math.round((completedCount / steps.length) * 100);

    // Dismiss handler
    const handleDismiss = () => {
        setDismissed(true);
        localStorage.setItem("onboarding_dismissed", "true");
    };

    // Don't show if dismissed, data loading, or already completed everything
    if (dismissed || agentsLoading || devicesLoading) return null;
    if (hasAgents && hasDevices) return null;

    const activeStep = steps[currentStep];

    // =====================================================================
    // MINIMIZED STATE — small floating button
    // =====================================================================
    if (isMinimized) {
        return (
            <button
                onClick={() => setIsMinimized(false)}
                className="fixed bottom-6 right-6 z-[9999] flex items-center gap-2 px-4 py-3 rounded-full text-white shadow-2xl hover:scale-105 transition-all duration-200"
                style={{ background: activeStep.gradient }}
                aria-label="Mở hướng dẫn"
            >
                <Rocket size={20} />
                <span className="text-sm font-medium hidden sm:inline">Hướng dẫn ({completedCount}/{steps.length})</span>
                <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold">
                    {completedCount}
                </div>
            </button>
        );
    }

    // =====================================================================
    // FULL WIZARD CARD
    // =====================================================================
    return (
        <div
            className="fixed bottom-6 right-6 z-[9999] w-[380px] max-w-[calc(100vw-32px)] rounded-2xl overflow-hidden shadow-2xl animate-fadeIn"
            style={{
                background: 'var(--apple-surface-primary)',
                border: '1px solid var(--apple-border-primary)',
            }}
        >
            {/* Header */}
            <div
                className="relative px-5 pt-5 pb-4"
                style={{ background: activeStep.gradient }}
            >
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3 text-white">
                        <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur-sm">
                            {activeStep.icon}
                        </div>
                        <div>
                            <Text className="text-white/70 text-xs font-medium block" style={{ color: 'rgba(255,255,255,0.7)' }}>
                                {activeStep.subtitle}
                            </Text>
                            <Title heading={5} style={{ color: '#fff', margin: 0 }}>
                                {activeStep.title}
                            </Title>
                        </div>
                    </div>
                    <div className="flex gap-1">
                        <button
                            onClick={() => setIsMinimized(true)}
                            className="w-7 h-7 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
                            aria-label="Thu nhỏ"
                            title="Thu nhỏ"
                        >
                            <span className="text-base leading-none">−</span>
                        </button>
                        <button
                            onClick={handleDismiss}
                            className="w-7 h-7 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
                            aria-label="Đóng hướng dẫn"
                            title="Ẩn vĩnh viễn"
                        >
                            <X size={14} />
                        </button>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3">
                    <Progress
                        percent={progressPercent}
                        showInfo={false}
                        size="small"
                        stroke="rgba(255,255,255,0.9)"
                        style={{ background: 'rgba(255,255,255,0.2)' }}
                    />
                </div>
            </div>

            {/* Body */}
            <div className="px-5 py-4">
                <Text className="text-sm leading-relaxed" style={{ color: 'var(--apple-text-secondary)' }}>
                    {activeStep.description}
                </Text>

                {/* Steps overview */}
                <div className="mt-4 space-y-2">
                    {steps.map((step, i) => {
                        const isComplete = step.checkComplete();
                        const isActive = i === currentStep;
                        return (
                            <div
                                key={step.id}
                                className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${isActive && !isComplete ? 'bg-[var(--apple-surface-tertiary)]' : ''}`}
                            >
                                {isComplete ? (
                                    <CheckCircle2 size={18} className="text-green-500 shrink-0" />
                                ) : isActive ? (
                                    <div className="w-[18px] h-[18px] rounded-full border-2 border-[var(--apple-blue)] flex items-center justify-center shrink-0">
                                        <div className="w-2 h-2 rounded-full bg-[var(--apple-blue)]" />
                                    </div>
                                ) : (
                                    <div className="w-[18px] h-[18px] rounded-full border-2 border-[var(--apple-gray-300)] shrink-0" />
                                )}
                                <Text
                                    size="small"
                                    style={{
                                        color: isComplete
                                            ? 'var(--apple-text-tertiary)'
                                            : isActive
                                                ? 'var(--apple-text-primary)'
                                                : 'var(--apple-text-quaternary)',
                                        textDecoration: isComplete ? 'line-through' : 'none',
                                        fontWeight: isActive ? 600 : 400,
                                    }}
                                >
                                    {step.title}
                                </Text>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Footer action */}
            <div className="px-5 pb-5">
                <Button
                    block
                    theme="solid"
                    type="primary"
                    size="large"
                    onClick={() => navigate(activeStep.actionRoute)}
                    style={{
                        background: activeStep.gradient.includes('10b981') ? '#10b981' : undefined,
                        borderRadius: 12,
                        height: 44,
                        fontWeight: 600,
                    }}
                    icon={activeStep.id === "complete" ? <Zap size={18} /> : undefined}
                >
                    <span className="flex items-center gap-2">
                        {activeStep.actionLabel}
                        <ArrowRight size={16} />
                    </span>
                </Button>

                {/* Quick Start - only shows on "Create Agent" step */}
                {activeStep.id === "create-agent" && (
                    <Button
                        block
                        theme="light"
                        type="tertiary"
                        size="default"
                        className="mt-2"
                        style={{ borderRadius: 10, height: 36 }}
                        onClick={async () => {
                            try {
                                const { default: apiClient } = await import("@/config/axios-instance");
                                const res = await apiClient.post("/user/onboarding-setup");
                                if (res.data?.success) {
                                    const { toast } = await import("sonner");
                                    toast.success(res.data.message || "Đã tạo Agent mặc định!");
                                    // Navigate to agent page
                                    if (res.data.agent_id) {
                                        navigate(`/agents/${res.data.agent_id}`);
                                    } else {
                                        navigate("/agents");
                                    }
                                }
                            } catch (e: any) {
                                console.error("Quick Start error:", e);
                                const { toast } = await import("sonner");
                                toast.error(e?.response?.data?.detail || "Lỗi tạo Agent nhanh");
                            }
                        }}
                    >
                        <span className="flex items-center gap-1.5 text-xs">
                            <Zap size={14} />
                            Tạo nhanh Agent mặc định
                        </span>
                    </Button>
                )}

                <button
                    onClick={handleDismiss}
                    className="w-full mt-2 text-center text-xs py-1 hover:underline transition-colors"
                    style={{ color: 'var(--apple-text-quaternary)' }}
                >
                    Tôi đã biết cách, bỏ qua
                </button>
            </div>
        </div>
    );
}

export default OnboardingWizard;
