import { useState } from "react";
import {
    Zap, Check, ArrowRight, Brain, Phone, ChevronDown,
    Briefcase, Home, Star, Quote,
    Sparkles, Mic, Volume2, Cpu,
    MessageSquare, Play, Pause,
    Fingerprint, Palette, Download, Database,
    Layers, MonitorSmartphone, Wand2,
    Wifi, Cloud, Bot, Workflow,
    Smile, Image, HardDrive,
    ArrowUpRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { BrandConfig } from "@/config/brands";

interface ModernLandingPageProps {
    brand: BrandConfig;
}

// ============================================================================
// DATA (Preserved from original)
// ============================================================================
const platformFeatures = [
    {
        category: "AI & Voice",
        icon: Brain,
        color: "from-violet-500 to-purple-600",
        features: [
            { icon: Mic, name: "Voice AI 24/7", desc: "Trợ lý giọng nói tiếng Việt mượt mà" },
            { icon: Bot, name: "Multi-LLM", desc: "Hỗ trợ 10+ nhà cung cấp AI hàng đầu" },
            { icon: MessageSquare, name: "Smart Chat", desc: "Luồng hội thoại tự nhiên, đa phương thức" },
        ]
    },
    {
        category: "IoT & Devices",
        icon: Cpu,
        color: "from-blue-500 to-cyan-500",
        features: [
            { icon: MonitorSmartphone, name: "Device Manager", desc: "Quản trị thiết bị tập trung, không giới hạn" },
            { icon: Download, name: "OTA Firmware", desc: "Cập nhật phần mềm thiết bị từ xa qua WiFi" },
            { icon: Wifi, name: "MQTT & WebSocket", desc: "Giao thức kết nối real-time, độ trễ cực thấp" },
            { icon: HardDrive, name: "Mở Rộng Phần Cứng", desc: "Hỗ trợ nền tảng ESP32, Rasp Pi, Arduino" },
        ]
    },
    {
        category: "Customization",
        icon: Palette,
        color: "from-pink-500 to-rose-500",
        features: [
            { icon: Image, name: "Asset Generator", desc: "Sinh đồ họa, hình ảnh tự động bằng AI" },
            { icon: Smile, name: "Emoji Packs", desc: "Xây dựng biểu cảm riêng cho thiết bị" },
            { icon: Layers, name: "Display Themes", desc: "Tùy biến giao diện hiển thị linh hoạt" },
            { icon: Wand2, name: "Template Builder", desc: "Tạo cấu hình AI Agent theo Use-case" },
        ]
    },
    {
        category: "Knowledge",
        icon: Database,
        color: "from-amber-500 to-orange-500",
        features: [
            { icon: Database, name: "Knowledge Base", desc: "Quản lý cơ sở tri thức (RAG) riêng tư" },
            { icon: Brain, name: "Memory AI", desc: "Bộ nhớ dài hạn, ghi nhớ bối cảnh người dùng" },
            { icon: Workflow, name: "MCP Protocol", desc: "Kết nối hệ sinh thái công cụ bên ngoài" },
            { icon: Cloud, name: "Cloud Sync", desc: "Đồng bộ dữ liệu tức thời mọi lúc, mọi nơi" },
        ]
    },
];

const coreHighlights = [
    {
        icon: Mic,
        title: "Giọng Trí Tuệ Nhân Tạo",
        subtitle: "Đa dạng tùy chọn",
        description: "Tích hợp nhiều Engine TTS chất lượng cao. Giọng đọc tự nhiên, phản hồi nhanh chóng.",
        gradient: "from-violet-500 to-fuchsia-600",
        stats: "Natural Voice"
    },
    {
        icon: Download,
        title: "OTA Firmware",
        subtitle: "Quản lý Không dây",
        description: "Triển khai phiên bản firmware cho hàng nghìn thiết bị. An toàn, bảo mật và hỗ trợ Rollback lập tức.",
        gradient: "from-blue-500 to-cyan-500",
        stats: "Zero Cable"
    },
    {
        icon: Wand2,
        title: "Asset Generator",
        subtitle: "Sáng Tạo Nội Dung",
        description: "Tích hợp sẵn luồng sinh ảnh từ Stable Diffusion & DALL-E, cấp hình ảnh động ngay trên màn hình.",
        gradient: "from-amber-500 to-orange-500",
        stats: "1-Click Gen"
    },
    {
        icon: Workflow,
        title: "Model Context Protocol",
        subtitle: "Mở rộng Không giới hạn",
        description: "Kết nối AI của bạn ra ngoài: Lịch, Email, Smart Home API hoặc Hệ thống Quản trị Doanh nghiệp nội bộ.",
        gradient: "from-emerald-500 to-teal-500",
        stats: "100+ Tools"
    },
];

const ttsFeatures = [
    {
        icon: Volume2,
        name: "Valtec Standard",
        description: "Tuyển tập 5 chất giọng tự nhiên chuẩn vùng miền",
        voices: ["Bắc Nữ", "Nam Nữ", "Bắc Nam 1", "Nam Nam", "Bắc Nam 2"],
        quality: "24kHz",
        speed: "Real-time"
    },
    {
        icon: Fingerprint,
        name: "Valtec Identity",
        description: "Tính năng siêu việt: Gọi hồn giọng nói chỉ trong vài giây",
        voices: ["Clone Your Voice", "Bình", "Ngọc Huyền", "Bác Sĩ Tuyên", "+3 Khác"],
        quality: "24kHz",
        speed: "3s/sentence"
    }
];

const useCases = [
    {
        id: "business",
        icon: Briefcase,
        title: "Kinh Doanh & Doanh Nghiệp",
        subtitle: "Triển khai Trợ lý AI",
        description: "Sử dụng Voice AI làm lễ tân tự động, CSKH qua màn hình Kiosk IoT hoặc hỗ trợ tra cứu Knowledge Base nội bộ.",
        features: ["Trực sảnh thông minh", "Tra cứu SOP", "Quản lý lịch họp tự động"],
        gradient: "from-violet-500 to-fuchsia-600",
        users: "500+"
    },
    {
        id: "smarthome",
        icon: Home,
        title: "Giải pháp Nhà Thông Minh",
        subtitle: "Điều khiển bằng Giọng nói",
        description: "Biến Xiaozhi thành điểm điều khiển trung tâm thay cho loa thông minh cổ điển tích hợp thẳng vào HomeAssistant.",
        features: ["Khởi chạy kịch bản (Automation)", "Liên kết cảm biến", "Thiết lập cảnh báo"],
        gradient: "from-emerald-500 to-teal-500",
        users: "2,000+"
    },
    {
        id: "maker",
        icon: Cpu,
        title: "Cộng Đồng Maker IoT",
        subtitle: "Hệ sinh thái cho Dev",
        description: "Môi trường hoàn hảo để phát triển sản phẩm Hardware nhúng tính năng AI tiên tiến và quản lý dễ dàng.",
        features: ["ESP-IDF integration", "Tùy biến GPIO", "Bypass AI pipeline"],
        gradient: "from-blue-500 to-cyan-500",
        users: "1,000+"
    },
];

const techStack = [
    { name: "OpenAI GPT-4o", logo: "🤖" },
    { name: "Google Gemini", logo: "✨" },
    { name: "Anthropic Claude", logo: "🧠" },
    { name: "ESP32 Ecosystem", logo: "📡" },
    { name: "Vite + React", logo: "⚡" },
];

const testimonialsData = [
    { name: "Anh Trần Minh Đức", role: "CEO Tech Startup", avatar: "👨‍💼", content: "Voice Clone của nền tảng này quá ấn tượng! Trợ lý ảo nói đúng giọng của tôi để trả lời đối tác khi tôi đang bận họp.", rating: 5 },
    { name: "Lê Hoàng", role: "IoT Engineer", avatar: "🧑‍💻", content: "Việc có sẵn OTA và MQTT bridge giúp team tiết kiệm hàng trăm giờ code backend. Giao diện quản lý cực kỳ trực quan sáng sủa.", rating: 5 },
    { name: "Chị Ngọc", role: "Quản lý Cửa Hàng", avatar: "👩‍💼", content: "Đã ứng dụng màn hình hiển thị Sales AI. Khách vào quán rất thích thú khi được hỏi đáp với màn hình trí tuệ nhân tạo.", rating: 5 },
];

const faqData = [
    { question: "OTA Firmware Firmware hỗ trợ các thiết bị nào?", answer: "Hiện tại nền tảng tập trung mạnh vào dòng chip ESP32 (đặc biệt là ESP32-S3), hỗ trợ update từ xa không cần cáp, kèm theo giao diện theo dõi tiến trình và tính năng hạ cấp (rollback)." },
    { question: "Tôi có được tự cung cấp API Key AI (BYOK) không và nó có an toàn không?", answer: "Hoàn toàn được. Nền tảng được thiết kế mở (Bring Your Own Key). API Key của OpenAI, Google Gemini, Anthropic... của bạn sẽ được mã hóa an toàn bằng thuật toán AES-256 HKDF độc lập cho từng người dùng (Zero-Knowledge Architecture), giúp bạn hoàn toàn an tâm khi tích hợp kết nối." },
    { question: "MCP Tools là gì?", answer: "MCP (Model Context Protocol) là một chuẩn do Anthropic giới thiệu. Nền tảng của chúng tôi kết nối thiết bị IoT của bạn tới hàng loạt công cụ ngoài như: Lấy tin thời tiết, Tra cứu lịch Google, Điều khiển đèn thông minh..." },
];

// ============================================================================
// MAIN COMPONENT (LIGHT MODE REDESIGN)
// ============================================================================
export function ModernLandingPage({ brand }: ModernLandingPageProps) {
    const [openFaq, setOpenFaq] = useState<number | null>(null);
    const [selectedUseCase, setSelectedUseCase] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const [activeCategory, setActiveCategory] = useState(0);

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-violet-200">
            {/* HEADER */}
            <header className="sticky top-0 z-50 bg-white/70 backdrop-blur-xl border-b border-slate-200 shadow-sm transition-all">
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        {brand.logo ? (
                            <img src={brand.logo} alt="XiaoZhi" className="h-8 w-auto" />
                        ) : (
                            <div className="w-10 h-10 bg-gradient-to-br from-violet-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-bold shadow-md shadow-violet-500/20">X</div>
                        )}
                        <span className="text-xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">XiaoZhi AI IoT</span>
                    </div>
                    <nav className="hidden md:flex items-center gap-8">
                        <a href="#features" className="text-sm font-semibold text-slate-600 hover:text-violet-600 transition-colors">Tính năng</a>
                        <a href="#deploy" className="text-sm font-semibold text-slate-600 hover:text-violet-600 transition-colors">Triển khai</a>
                        <a href="#faq" className="text-sm font-semibold text-slate-600 hover:text-violet-600 transition-colors">Hỏi đáp</a>
                        <span className="w-px h-5 bg-slate-200"></span>
                        <a href="/asset-generator" className="flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-violet-600 transition-colors">
                            <Wand2 className="w-3.5 h-3.5" />Assets
                        </a>
                        <a href="/tools/flasher" className="flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-violet-600 transition-colors">
                            <Download className="w-3.5 h-3.5" />Flasher
                        </a>
                    </nav>
                    <div className="flex items-center gap-3">
                        <a href="/login">
                            <Button variant="ghost" className="text-slate-600 hover:text-violet-700 hover:bg-violet-50 font-medium">Đăng nhập</Button>
                        </a>
                        <Button className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 rounded-full px-6 shadow-md shadow-violet-600/20 border border-violet-500/50">
                            Bắt đầu tạo AI
                        </Button>
                    </div>
                </div>
            </header>

            {/* =========================================================== */}
            {/* HERO SECTION */}
            {/* =========================================================== */}
            <section className="relative pt-24 pb-32 lg:pt-32 lg:pb-40 overflow-hidden isolate">
                {/* Abstract Light Background Elements */}
                <div className="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80" aria-hidden="true">
                    <div className="relative left-[calc(50%-11rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-violet-200 to-fuchsia-100 opacity-60 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem]"></div>
                </div>
                <div className="absolute inset-0 -z-10 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.015] mix-blend-overlay pointer-events-none"></div>

                <div className="container mx-auto px-4">
                    <div className="text-center max-w-5xl mx-auto flex flex-col items-center">
                        {/* Status Badge */}
                        <div className="inline-flex items-center gap-2 bg-white border border-slate-200 shadow-sm px-4 py-2 rounded-full text-sm mb-8 animate-fade-in-up">
                            <Sparkles className="w-4 h-4 text-amber-500" />
                            <span className="text-slate-700 font-medium">Nền tảng Tích hợp Cận biên thông minh</span>
                            <span className="bg-violet-100 text-violet-700 font-bold text-xs px-2 py-0.5 rounded-full">Phiên bản 2.0</span>
                        </div>

                        {/* Main Headline */}
                        <h1 className="text-5xl md:text-[5.5rem] font-extrabold tracking-tight leading-[1.1] mb-8 text-slate-900 relative">
                            Nền tảng <span className="bg-gradient-to-r from-violet-600 via-indigo-500 to-cyan-500 bg-clip-text text-transparent">AI & IoT</span> <br className="hidden md:block"/> Thiết Kế Riêng Biệt
                        </h1>

                        {/* Subtitle */}
                        <p className="text-xl text-slate-600 leading-relaxed mb-10 max-w-2xl mx-auto font-medium">
                            Khai phá khả năng của thiết bị thông minh với <span className="text-violet-600 font-semibold">Công nghệ Nhân bản Giọng nói</span>, triển khai Firmware qua mạng và tự động gọi API ngữ cảnh phức tạp.
                        </p>

                        {/* Feature Pills */}
                        <div className="flex flex-wrap justify-center gap-3 mb-12">
                            {["11+ Studio Voices", "Voice Clone Live", "OTA Flash", "Kiosk Mode", "AI Memory", "MQTT Pipeline"].map((f, i) => (
                                <span key={i} className="px-4 py-2 bg-white border border-slate-200 rounded-full text-sm font-medium text-slate-600 shadow-sm hover:border-violet-300 hover:text-violet-700 transition duration-300">
                                    {f}
                                </span>
                            ))}
                        </div>

                        {/* CTA Buttons */}
                        <div className="flex flex-col sm:flex-row justify-center items-center gap-4 mb-20 w-full max-w-md mx-auto">
                            <Button size="lg" className="h-14 px-8 text-lg rounded-full bg-slate-900 text-white w-full sm:w-auto hover:bg-slate-800 shadow-xl shadow-slate-900/10">
                                Trải nghiệm AI Ngay <ArrowUpRight className="ml-2 w-5 h-5 text-violet-400" />
                            </Button>
                            <Button size="lg" variant="outline" className="h-14 px-8 text-lg rounded-full bg-white border-slate-200 text-slate-700 w-full sm:w-auto hover:bg-slate-50 hover:text-slate-900 shadow-sm">
                                <Play className="mr-2 w-5 h-5 text-slate-400" /> Xem Video HD
                            </Button>
                        </div>

                        {/* Metric Highlights */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 w-full max-w-4xl border-t border-slate-200 pt-10">
                            {[
                                { value: "10,000+", label: "Lượt tương tác" },
                                { value: "11 Mẫu", label: "Giọng đọc Cao cấp" },
                                { value: "10+", label: "Hệ tri thức LLM" },
                                { value: "0ms delay", label: "Routing Nội bộ" },
                            ].map((stat, i) => (
                                <div key={i} className="text-center group">
                                    <div className="text-4xl font-extrabold text-slate-900 group-hover:-translate-y-1 transition-transform">{stat.value}</div>
                                    <div className="text-sm font-medium text-slate-500 mt-1">{stat.label}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

             {/* =========================================================== */}
             {/* SPONSOR SECTION */}
             {/* =========================================================== */}
             <section className="py-10 bg-[#0A192F] border-y border-slate-800">
                <div className="container mx-auto px-4 text-center">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Được Cung Cấp Hệ Thống Đám Mây Bởi</p>
                    <div className="flex justify-center items-center opacity-90 hover:opacity-100 transition-opacity">
                        <img src="https://eztech.vn/wp-content/uploads/2024/09/logo-eztech.png" alt="EzTech" className="h-12 transition-all duration-500 filter drop-shadow-[0_2px_8px_rgba(255,255,255,0.1)]" />
                    </div>
                </div>
            </section>

            {/* =========================================================== */}
            {/* PLATFORM FEATURES - Glassmorphism UI */}
            {/* =========================================================== */}
            <section id="features" className="py-24 bg-slate-50 relative">
                <div className="container mx-auto px-4">
                    <div className="text-center mb-16 max-w-3xl mx-auto">
                        <Badge className="mb-4 bg-violet-100 text-violet-700 border-none px-3 py-1 text-sm font-semibold">Tích Hợp Sâu</Badge>
                        <h2 className="text-4xl lg:text-5xl font-extrabold mb-6 text-slate-900">
                            Công nghệ Cốt lõi cho <br className="hidden md:block"/><span className="bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">Giải pháp Phức tạp</span>
                        </h2>
                        <p className="text-slate-600 text-lg">Hệ thống hợp nhất giữa phần mềm quản trị AI và vi mạch phần cứng IoT đem tới một trải nghiệm điều khiển liền mạch ở lớp sâu nhất.</p>
                    </div>

                    {/* Category Tabs */}
                    <div className="flex flex-wrap justify-center gap-3 mb-12 bg-white p-1.5 rounded-full shadow-sm border border-slate-200 w-fit mx-auto">
                        {platformFeatures.map((cat, idx) => (
                            <button
                                key={idx}
                                onClick={() => setActiveCategory(idx)}
                                className={`flex items-center gap-2 px-6 py-2.5 rounded-full font-semibold transition-all ${activeCategory === idx
                                    ? `bg-slate-900 text-white shadow-md`
                                    : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
                                    }`}
                            >
                                <cat.icon className="w-4 h-4" />
                                {cat.category}
                            </button>
                        ))}
                    </div>

                    {/* Features Grid */}
                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
                        {platformFeatures[activeCategory].features.map((feature, idx) => (
                            <div
                                key={idx}
                                className="group bg-white border border-slate-200 rounded-3xl p-8 hover:shadow-[0_8px_30px_rgb(0,0,0,0.06)] hover:border-violet-200 transition-all duration-300 translate-y-0 hover:-translate-y-1"
                            >
                                <div className={`w-14 h-14 bg-gradient-to-br ${platformFeatures[activeCategory].color} rounded-2xl flex items-center justify-center mb-6 shadow-sm group-hover:shadow-md transition-all`}>
                                    <feature.icon className="w-6 h-6 text-white" />
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-3">{feature.name}</h3>
                                <p className="text-slate-600 text-sm leading-relaxed">{feature.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* =========================================================== */}
            {/* CORE HIGHLIGHTS GRID */}
            {/* =========================================================== */}
            <section className="py-24 bg-white relative border-y border-slate-100">
                <div className="container mx-auto px-4">
                    <div className="flex flex-col md:flex-row items-end justify-between mb-16 max-w-6xl mx-auto">
                        <div>
                            <h2 className="text-4xl lg:text-5xl font-extrabold text-slate-900">
                                <span className="bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">Đột phá</span> Công nghệ
                            </h2>
                        </div>
                        <p className="text-slate-500 font-medium max-w-sm mt-6 md:mt-0 leading-relaxed text-lg">
                            Các đặc tả nổi bật hoàn toàn vượt qua các phương thức IoT truyền thống.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
                        {coreHighlights.map((item, idx) => (
                            <div key={idx} className="bg-slate-50 border border-slate-200 rounded-[2rem] p-8 hover:bg-white hover:shadow-xl transition-all duration-300 group">
                                <div className="flex justify-between items-start mb-8">
                                    <div className={`p-4 rounded-2xl bg-white shadow-sm border border-slate-100 text-violet-600 group-hover:scale-110 transition-transform`}>
                                        <item.icon className="w-6 h-6" />
                                    </div>
                                    <span className="text-xs font-bold text-slate-500 bg-slate-200/50 px-3 py-1 rounded-full">
                                        {item.stats}
                                    </span>
                                </div>
                                <h3 className="text-xl font-bold text-slate-900 mb-2">{item.title}</h3>
                                <p className="text-sm font-semibold text-violet-600 mb-4">{item.subtitle}</p>
                                <p className="text-slate-600 text-sm leading-relaxed">{item.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* =========================================================== */}
            {/* CÀI ĐẶT SERVER */}
            {/* =========================================================== */}
            <section id="installation" className="py-24 bg-white border-t border-slate-200/50">
                <div className="container mx-auto px-4 max-w-4xl">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-extrabold text-slate-900 mb-4">Hướng Dẫn Cài Đặt Server</h2>
                        <p className="text-slate-500">Tự triển khai máy chủ Xiaozhi CE của riêng bạn chỉ với vài thao tác cơ bản.</p>
                    </div>

                    <div className="bg-white border border-slate-200 rounded-3xl p-8 md:p-12 shadow-xl overflow-hidden relative">
                        <div className="absolute top-0 right-0 p-8 opacity-[0.03]">
                            <Database className="w-48 h-48 text-violet-600" />
                        </div>
                        
                        <div className="relative z-10 space-y-8">
                            {/* Step 1 */}
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-8 h-8 rounded-full bg-violet-500 flex items-center justify-center text-white font-bold">1</div>
                                    <h3 className="text-xl font-bold text-slate-900">Yêu Cầu Hệ Thống</h3>
                                </div>
                                <ul className="list-disc list-inside text-slate-600 ml-11 space-y-2">
                                    <li>Máy chủ Linux (Ubuntu/Debian) có kết nối Internet.</li>
                                    <li>Cài đặt sẵn Docker và Docker Compose.</li>
                                    <li>Có ít nhất một API Key của các nhà cung cấp AI (OpenAI, Gemini, DeepSeek).</li>
                                </ul>
                            </div>

                            {/* Step 2 */}
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-8 h-8 rounded-full bg-violet-500 flex items-center justify-center text-white font-bold">2</div>
                                    <h3 className="text-xl font-bold text-slate-900">Clone Mã Nguồn</h3>
                                </div>
                                <div className="ml-11 bg-slate-100 rounded-xl p-4 font-mono text-sm text-slate-800 overflow-x-auto border border-slate-200">
                                    git clone https://github.com/nguyenduchoai/Server-Xiaozhi-PY-Vietnam.git<br/>
                                    cd Server-Xiaozhi-PY-Vietnam
                                </div>
                            </div>

                            {/* Step 3 */}
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-8 h-8 rounded-full bg-violet-500 flex items-center justify-center text-white font-bold">3</div>
                                    <h3 className="text-xl font-bold text-slate-900">Cấu Hình Môi Trường</h3>
                                </div>
                                <p className="text-slate-600 ml-11 mb-2">Tạo file cấu hình từ file mẫu và điền các thông tin bảo mật của bạn (Mật khẩu Admin, API Keys):</p>
                                <div className="ml-11 bg-slate-100 rounded-xl p-4 font-mono text-sm text-slate-800 overflow-x-auto border border-slate-200">
                                    cp .env.example .env<br/>
                                    nano .env
                                </div>
                            </div>

                            {/* Step 4 */}
                            <div>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-8 h-8 rounded-full bg-violet-500 flex items-center justify-center text-white font-bold">4</div>
                                    <h3 className="text-xl font-bold text-slate-900">Khởi Chạy Dịch Vụ</h3>
                                </div>
                                <p className="text-slate-600 ml-11 mb-2">Khởi động tất cả các container nền tảng bằng Docker Compose:</p>
                                <div className="ml-11 bg-slate-100 rounded-xl p-4 font-mono text-sm text-slate-800 overflow-x-auto border border-slate-200">
                                    docker compose up -d
                                </div>
                            </div>
                            
                            {/* Note */}
                            <div className="ml-11 mt-6 bg-violet-50 border border-violet-200 rounded-xl p-6">
                                <h4 className="text-violet-700 font-bold flex items-center gap-2 mb-2"><Sparkles className="w-5 h-5"/> Kết Nối Thiết Bị</h4>
                                <p className="text-slate-600 text-sm">
                                    Nếu bạn dùng firmware chuẩn Xiaozhi, chỉ cần đổi địa chỉ <strong className="text-slate-900">OTA URL</strong> về máy chủ này, thiết bị sẽ tự động tải bản cập nhật và kết nối tới MQTT của bạn. Tất cả dữ liệu và API Key được mã hóa một chiều hoàn toàn an toàn (BYOK - Zero Knowledge).
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* =========================================================== */}
            {/* FAQ */}
            {/* =========================================================== */}
            <section id="faq" className="py-24 bg-slate-50 border-t border-slate-200/50">
                <div className="container mx-auto px-4 max-w-3xl">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-extrabold text-slate-900 mb-4">Câu Hỏi Thường Gặp</h2>
                        <p className="text-slate-500">Mọi thắc mắc kỹ thuật được giải thích cặn kẽ.</p>
                    </div>

                    <div className="space-y-4">
                        {faqData.map((faq, idx) => (
                            <div key={idx} className={`bg-white border rounded-2xl transition-all shadow-sm ${openFaq === idx ? 'border-violet-400 ring-2 ring-violet-50' : 'border-slate-200 hover:border-slate-300'}`}>
                                <button onClick={() => setOpenFaq(openFaq === idx ? null : idx)} className="w-full p-6 flex items-center justify-between text-left focus:outline-none">
                                    <span className="font-bold text-slate-800 pr-4">{faq.question}</span>
                                    <ChevronDown className={`w-5 h-5 shrink-0 transition-transform duration-300 ${openFaq === idx ? 'rotate-180 text-violet-600' : 'text-slate-400'}`} />
                                </button>
                                <div className={`overflow-hidden transition-all duration-300 ease-in-out ${openFaq === idx ? 'max-h-48 opacity-100' : 'max-h-0 opacity-0'}`}>
                                    <div className="px-6 pb-6 text-slate-600 leading-relaxed bg-slate-50/50 pt-2 border-t border-slate-50">
                                        {faq.answer}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* =========================================================== */}
            {/* CTA */}
            {/* =========================================================== */}
            <section className="py-28 relative overflow-hidden border-t border-slate-200">
                <div className="absolute inset-0 bg-violet-50"></div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl h-full bg-violet-300/30 blur-[120px] rounded-full pointer-events-none"></div>
                
                <div className="container mx-auto px-4 text-center relative z-10">
                    <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 mb-6 tracking-tight">
                        Kiến Tạo Ngay Giải Pháp Của Bạn
                    </h2>
                    <p className="text-xl text-slate-600 mb-10 max-w-2xl mx-auto font-medium">
                        Tích hợp các dòng lệnh AI mạnh mẽ nhất vào nền vi mạch cực nhỏ. Tất cả đều diễn ra mượt mà và trực quan.
                    </p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <Button size="lg" className="h-14 px-10 text-lg bg-slate-900 text-white hover:bg-slate-800 rounded-full font-bold shadow-xl border border-transparent">
                            <Wand2 className="mr-2 w-5 h-5 text-violet-400" /> Bắt đầu tạo Workspace
                        </Button>
                    </div>
                </div>
            </section>

            {/* =========================================================== */}
            {/* FOOTER */}
            {/* =========================================================== */}
            <footer className="bg-slate-50 border-t border-slate-200 py-16">
                <div className="container mx-auto px-4">
                    <div className="grid md:grid-cols-5 gap-12 mb-12">
                        <div className="md:col-span-2 space-y-4">
                            <div className="flex items-center gap-2">
                                <div className="w-10 h-10 bg-gradient-to-br from-violet-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-bold shadow-md">X</div>
                                <span className="text-xl font-bold text-slate-900 tracking-tight">XiaoZhi AI IoT</span>
                            </div>
                            <p className="text-sm font-medium text-slate-500 max-w-xs mt-4">Nền tảng Tích hợp AI toàn diện dẫn đầu lĩnh vực phần cứng vi điều khiển và xử lý ngôn ngữ giao tiếp tại VN.</p>
                        </div>
                        <div className="space-y-4">
                            <h4 className="font-bold text-slate-900">Nền Tảng</h4>
                            <ul className="space-y-3 text-sm font-medium text-slate-500">
                                <li><a href="#" className="hover:text-violet-600 transition-colors">Công nghệ Voice AI</a></li>
                                <li><a href="#" className="hover:text-violet-600 transition-colors">Bản Quyền Firmware</a></li>
                                <li><a href="#" className="hover:text-violet-600 transition-colors">Dev Toolkit</a></li>
                            </ul>
                        </div>
                        <div className="space-y-4">
                            <h4 className="font-bold text-slate-900">Giải Pháp</h4>
                            <ul className="space-y-3 text-sm font-medium text-slate-500">
                                <li><a href="#" className="hover:text-violet-600 transition-colors">Kiosk Lễ Tân (B2B)</a></li>
                                <li><a href="#" className="hover:text-violet-600 transition-colors">Smart Home (B2C)</a></li>
                                <li><a href="#" className="hover:text-violet-600 transition-colors">Hệ Sinh Thái RAG</a></li>
                            </ul>
                        </div>
                        <div className="space-y-4">
                            <h4 className="font-bold text-slate-900">Liên hệ</h4>
                            <ul className="space-y-3 text-sm font-medium text-slate-500">
                                <li>Email: contact@xiaozhi-ai-iot.vn</li>
                            </ul>
                        </div>
                    </div>
                    <div className="border-t border-slate-200 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
                        <p className="text-sm font-semibold text-slate-400">© 2026 XiaoZhi AI IoT Việt Nam. Đã đăng ký bản quyền.</p>
                        <div className="flex gap-6 text-sm font-semibold text-slate-400">
                            <a href="/terms" className="hover:text-violet-600 transition-colors">Điều khoản Sử dụng</a>
                            <a href="/privacy" className="hover:text-violet-600 transition-colors">Chính sách Bảo mật</a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}

// Export aliases for backward compatibility
export { ModernLandingPage as XiaozhiLandingPage };

