// Icon strings are used, not components
// import { Bot, Shield, TrendingUp, Users, Zap, Check, Cpu, Brain, MessageSquare } from "lucide-react";

export interface SiteHomeSettings {
    hero: {
        hero_title: string;
        hero_subtitle: string;
        hero_badge_text: string;
        hero_cta_primary: string;
        hero_cta_secondary: string;
    };
    features: {
        features_enabled: boolean;
        features_title: string;
        features_subtitle: string;
        features_list: Array<{ icon: string; title: string; description: string }>;
    };
    pricing: {
        pricing_enabled: boolean;
        pricing_title: string;
        pricing_subtitle: string;
    };
    cta: {
        cta_enabled: boolean;
        cta_title: string;
        cta_subtitle: string;
        cta_button_text: string;
    };
    testimonials: {
        testimonials_enabled: boolean;
        testimonials_title: string;
        testimonials_subtitle: string;
        testimonials_list: Array<{ id: number; name: string; role: string; content: string; avatar: string; rating: number }>;
    };
    footer: {
        footer_brand_description: string;
        footer_copyright: string;
        footer_address: string;
        footer_social_facebook: string;
        footer_social_twitter: string;
        footer_social_linkedin: string;
    };
    menu: {
        menu_items: Array<{ label: string; href: string; external: boolean }>;
    };
}

export interface BrandConfig {
    id: string;
    name: string;
    theme: "default" | "playful" | "business" | "tech";
    logo?: string;
    content: SiteHomeSettings;
}

export const defaultBrandConfig: BrandConfig = {
    id: "xiaozhi",
    name: "XiaoZhi AI IoT Việt Nam",
    theme: "playful",
    logo: "https://minigame.xiaozhi-ai-iot.vn/assets/images/logo.jpg",
    content: {
        hero: {
            hero_title: "Chào! Tớ là XiaoZhi AI 👋",
            hero_subtitle: "Tớ là một trợ lý ảo siêu thông minh (và dễ thương!). Tớ có thể nói chuyện, điều khiển đèn LED, lập trình ESP32 và làm đủ trò vui với giao thức MCP.",
            hero_badge_text: "✨ Chatbot + IoT + Magic ✨",
            hero_cta_primary: "Chơi với XiaoZhi ngay!",
            hero_cta_secondary: "Xem Video Demo",
        },
        features: {
            features_enabled: true,
            features_title: "XiaoZhi làm được gì nhỉ?",
            features_subtitle: "Không chỉ là Chatbot, tớ là cầu nối giữa thế giới ảo và thực ✨",
            features_list: [
                { icon: "MessageSquare", title: "Trò chuyện dí dỏm", description: "Tớ (Tiểu Trí) có thể tâm sự, kể chuyện cười và là 'đại tỷ tỷ' (Xiao Jie Jie) đáng tin cậy của bạn." },
                { icon: "Cpu", title: "Điều khiển IoT cực ngầu", description: "Bảo tớ: 'Bật đèn xanh', 'Quạt quay nhanh lên' - ESP32/ESP8266 sẽ vâng lời tớ ngay lập tức!" },
                { icon: "Brain", title: "Giao thức MCP xịn xò", description: "Model Context Protocol cho phép tớ hiểu sâu và tác động thật vào thế giới vật lý." },
            ],
        },
        pricing: {
            pricing_enabled: false,
            pricing_title: "",
            pricing_subtitle: "",
        },
        cta: {
            cta_enabled: true,
            cta_title: "Kết bạn với XiaoZhi nhé?",
            cta_subtitle: "Tham gia cộng đồng AI IoT vui nhộn nhất hệ mặt trời 🚀",
            cta_button_text: "Tạo tài khoản miễn phí",
        },
        testimonials: {
            testimonials_enabled: true,
            testimonials_title: "Fan hâm mộ nói gì?",
            testimonials_subtitle: "Các maker và lập trình viên đều yêu quý Tiểu Trí",
            testimonials_list: [
                {
                    id: 1,
                    name: "Coder 'Giấu Tên'",
                    role: "IoT Maker",
                    content: "XiaoZhi quá đỉnh! Mình kết nối ESP32 chỉ trong 5 phút. Giờ mình ra lệnh giọng nói là đèn nháy theo nhạc.",
                    avatar: "https://ui-avatars.com/api/?name=Coder+X&background=F59E0B&color=fff",
                    rating: 5,
                },
                {
                    id: 2,
                    name: "Mèo Mun",
                    role: "Sinh viên IT",
                    content: "Thích gọi là 'Tiểu Trí' hay 'Tỷ Tỷ' đều được, AI phản hồi rất tự nhiên và cute. 10 điểm!",
                    avatar: "https://ui-avatars.com/api/?name=Meo+Mun&background=10B981&color=fff",
                    rating: 5,
                }
            ],
        },
        footer: {
            footer_brand_description: "XiaoZhi AI (Tiểu Trí) - Trợ lý ảo AI IoT thân thiện nhất.",
            footer_copyright: "© 2025 Xiaozhi AI IoT. All rights reserved.",
            footer_address: "Cyberpunk City, Internet",
            footer_social_facebook: "",
            footer_social_twitter: "",
            footer_social_linkedin: "",
        },
        menu: {
            menu_items: [
                { label: "Tiểu Trí là ai?", href: "#features", external: false },
                { label: "Fan nói gì?", href: "#testimonials", external: false },
                { label: "Kết bạn", href: "#contact", external: false },
            ],
        },
    }
};

export const brandConfigs: Record<string, BrandConfig> = {
    // ========================================================================
    // Xiaozhi AI IoT (Minigame / Playful / MCP Focus)
    // ========================================================================
    "default": defaultBrandConfig,
    "xiaozhi-ai-iot.vn": defaultBrandConfig,
};
