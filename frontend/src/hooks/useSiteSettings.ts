/**
 * useSiteSettings Hook
 * 
 * Fetches and caches site settings from API for use in Landing Pages.
 * Uses React Query for caching with 5-minute stale time.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/config/axios-instance";

// Types for site settings
export interface HeroStat {
    value: string;
    label: string;
}

export interface SolutionItem {
    id: string;
    icon: string;
    title: string;
    subtitle: string;
    description: string;
    features: string[];
    use_cases: string[];
    gradient: string;
    stats_value: string;
    stats_label: string;
}

export interface FAQItem {
    question: string;
    answer: string;
}

export interface FeatureItem {
    icon: string;
    title: string;
    description: string;
}

export interface TestimonialItem {
    id: number;
    name: string;
    role: string;
    content: string;
    avatar: string;
    rating: number;
}

export interface MenuItem {
    label: string;
    href: string;
    external: boolean;
}

export interface SiteSettings {
    web: {
        site_name: string;
        site_description: string;
        site_logo: string;
        primary_color: string;
        contact_email: string;
        support_phone: string;
    };
    payment: {
        bank_name: string;
        bank_code: string;
        account_number: string;
        account_name: string;
        bank_branch: string;
        transfer_content_template: string;
        enable_qr_code: boolean;
    };
    branding: {
        parent_company_name: string;
        parent_company_url: string;
        company_badge_text: string;
    };
    home: {
        hero: {
            hero_title: string;
            hero_subtitle: string;
            hero_badge_text: string;
            hero_cta_primary: string;
            hero_cta_secondary: string;
        };
        hero_stats: {
            hero_stats: HeroStat[];
        };
        features: {
            features_enabled: boolean;
            features_title: string;
            features_subtitle: string;
            features_list: FeatureItem[];
        };
        solutions: {
            solutions_enabled: boolean;
            solutions_title: string;
            solutions_subtitle: string;
            solutions_list: SolutionItem[];
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
            cta_button_secondary_text: string;
            cta_button_secondary_href: string;
        };
        testimonials: {
            testimonials_enabled: boolean;
            testimonials_title: string;
            testimonials_subtitle: string;
            testimonials_list: TestimonialItem[];
        };
        faq: {
            faq_enabled: boolean;
            faq_title: string;
            faq_subtitle: string;
            faq_list: FAQItem[];
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
            menu_items: MenuItem[];
        };
    };
}

/**
 * Fetch site settings from API
 */
async function fetchSiteSettings(): Promise<SiteSettings> {
    const { data } = await apiClient.get("/site-settings");
    return data;
}

/**
 * Hook to get site settings with caching
 * 
 * @example
 * const { data: settings, isLoading, error } = useSiteSettings();
 * const heroTitle = settings?.home?.hero?.hero_title || "Default Title";
 */
export function useSiteSettings() {
    return useQuery({
        queryKey: ["site-settings"],
        queryFn: fetchSiteSettings,
        staleTime: 5 * 60 * 1000, // 5 minutes cache
        gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
        refetchOnWindowFocus: false,
        retry: 2,
    });
}

/**
 * Get a specific setting value with fallback
 */
export function getSettingValue<T>(
    settings: SiteSettings | undefined,
    path: string,
    fallback: T
): T {
    if (!settings) return fallback;

    const keys = path.split(".");
    let value: unknown = settings;

    for (const key of keys) {
        if (value && typeof value === "object" && key in value) {
            value = (value as Record<string, unknown>)[key];
        } else {
            return fallback;
        }
    }

    return (value as T) ?? fallback;
}

export default useSiteSettings;
