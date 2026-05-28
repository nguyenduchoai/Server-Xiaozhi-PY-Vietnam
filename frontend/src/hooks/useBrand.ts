import { useState, useEffect } from 'react';
import { brandConfigs, defaultBrandConfig, type BrandConfig } from '@/config/brands';

// Helper to get hostname
const getHostname = () => window.location.hostname;

export function useBrand() {
    const [brand, setBrand] = useState<BrandConfig>(defaultBrandConfig);

    useEffect(() => {
        // 1. Check URL param override (for testing)
        const searchParams = new URLSearchParams(window.location.search);
        const brandOverride = searchParams.get('brand');

        // 2. Initial detection
        const hostname = getHostname();

        // Domain mapping logic
        // We match the exact key in brandConfigs, or fallback to default
        let determinedBrand = defaultBrandConfig;

        if (brandOverride && brandConfigs[brandOverride]) {
            // Manual override: ?brand=xiaozhi-ai-iot.vn
            determinedBrand = brandConfigs[brandOverride];
        } else if (brandConfigs[hostname]) {
            // Exact match: xiaozhi-ai-iot.vn
            determinedBrand = brandConfigs[hostname];
        } else {
            // Try to find by partial match (e.g. if running on localhost but want to test)
            // Or map specific domains to configs
            const foundKey = Object.keys(brandConfigs).find(key => hostname.includes(key));

            if (foundKey) {
                determinedBrand = brandConfigs[foundKey];
            }
        }

        setBrand(determinedBrand);

        // Dynamic Title Update
        document.title = determinedBrand.content.hero.hero_badge_text
            ? `${determinedBrand.content.hero.hero_badge_text} - ${determinedBrand.name}`
            : determinedBrand.name;

        // Set theme attribute for CSS styling
        document.documentElement.setAttribute('data-brand-theme', determinedBrand.theme);

    }, []);

    return brand;
}
