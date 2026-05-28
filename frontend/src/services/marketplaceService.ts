/**
 * Marketplace Service - API client cho Skill Marketplace
 */
import apiClient from "@/config/axios-instance";

// ==================== Types ====================

export interface Skill {
    id: string;
    name: string;
    slug: string;
    description: string;
    short_description?: string;
    skill_type: string;
    category: string;
    tags?: string[];
    config: Record<string, unknown>;
    author_id: string;
    author_name: string;
    author_verified: boolean;
    version: string;
    icon_url?: string;
    banner_url?: string;
    screenshots?: string[];
    install_count: number;
    rating: number;
    rating_count: number;
    is_public: boolean;
    is_verified: boolean;
    is_featured: boolean;
    is_premium: boolean;
    price?: number;
}

export interface SkillDetail extends Skill {
    readme?: string;
    screenshots?: string[];
    changelog?: string;
    documentation_url?: string;
}

export interface SkillCreate {
    name: string;
    slug: string;
    description: string;
    short_description?: string;
    skill_type?: string;
    category?: string;
    tags?: string[];
    config: Record<string, unknown>;
    version?: string;
    readme?: string;
    icon_url?: string;
    banner_url?: string;
    screenshots?: string[];
    is_premium?: boolean;
    price?: number;
    is_public?: boolean;
    is_featured?: boolean;
}

export interface SkillUpdate {
    name?: string;
    description?: string;
    short_description?: string;
    category?: string;
    tags?: string[];
    config?: Record<string, unknown>;
    version?: string;
    readme?: string;
    icon_url?: string;
    banner_url?: string;
    screenshots?: string[];
    is_public?: boolean;
    is_premium?: boolean;
    price?: number;
    is_featured?: boolean;
}

export interface SkillInstallation {
    id: string;
    skill_id: string;
    skill_name: string;
    skill_icon?: string;
    version_installed: string;
    installed_at: string;
    is_active: boolean;
}

export interface SkillReview {
    id: string;
    user_id: string;
    rating: number;
    title?: string;
    comment?: string;
    version_reviewed: string;
    helpful_count: number;
    created_at: string;
}

export interface SkillReviewCreate {
    rating: number;
    title?: string;
    comment?: string;
}

export interface SkillCategory {
    value: string;
    label: string;
    icon?: string;
    count?: number;
}

export interface BrowseParams {
    category?: string;
    skill_type?: string;
    search?: string;
    sort?: "popular" | "newest" | "rating";
    page?: number;
    page_size?: number;
}

export interface PaginatedResponse<T> {
    success: boolean;
    data: T[];
    total: number;
    page: number;
    page_size: number;
}

export interface SuccessResponse<T> {
    success: boolean;
    message?: string;
    data: T;
}

// ==================== Service ====================

const marketplaceService = {
    /**
     * Browse available skills
     */
    browseSkills: async (params?: BrowseParams): Promise<PaginatedResponse<Skill>> => {
        const response = await apiClient.get("/marketplace/skills", { params });
        return response.data;
    },

    /**
     * Get featured skills
     */
    getFeaturedSkills: async (limit: number = 10): Promise<SuccessResponse<Skill[]>> => {
        const response = await apiClient.get("/marketplace/skills/featured", {
            params: { limit },
        });
        return response.data;
    },

    /**
     * Get skill categories
     */
    getCategories: async (): Promise<SuccessResponse<SkillCategory[]>> => {
        const response = await apiClient.get("/marketplace/categories");
        return response.data;
    },

    /**
     * Get skill detail
     */
    getSkillDetail: async (skillId: string): Promise<SuccessResponse<SkillDetail>> => {
        const response = await apiClient.get(`/marketplace/skills/${skillId}`);
        return response.data;
    },

    /**
     * Get my created skills
     */
    getMySkills: async (): Promise<SuccessResponse<Skill[]>> => {
        const response = await apiClient.get("/marketplace/my-skills");
        return response.data;
    },

    /**
     * Create a new skill
     */
    createSkill: async (data: SkillCreate): Promise<SuccessResponse<Skill>> => {
        const response = await apiClient.post("/marketplace/skills", data);
        return response.data;
    },

    /**
     * Update a skill
     */
    updateSkill: async (skillId: string, data: SkillUpdate): Promise<SuccessResponse<Skill>> => {
        const response = await apiClient.put(`/marketplace/skills/${skillId}`, data);
        return response.data;
    },

    /**
     * Delete a skill
     */
    deleteSkill: async (skillId: string): Promise<void> => {
        await apiClient.delete(`/marketplace/skills/${skillId}`);
    },

    /**
     * Get installed skills
     */
    getInstalledSkills: async (): Promise<SuccessResponse<SkillInstallation[]>> => {
        const response = await apiClient.get("/marketplace/installations");
        return response.data;
    },

    /**
     * Install a skill
     */
    installSkill: async (skillId: string): Promise<SuccessResponse<SkillInstallation>> => {
        const response = await apiClient.post(`/marketplace/skills/${skillId}/install`);
        return response.data;
    },

    /**
     * Uninstall a skill
     */
    uninstallSkill: async (skillId: string): Promise<void> => {
        await apiClient.delete(`/marketplace/skills/${skillId}/uninstall`);
    },

    /**
     * Get skill reviews
     */
    getSkillReviews: async (
        skillId: string,
        params?: { page?: number; page_size?: number }
    ): Promise<PaginatedResponse<SkillReview>> => {
        const response = await apiClient.get(`/marketplace/skills/${skillId}/reviews`, { params });
        return response.data;
    },

    /**
     * Create a review
     */
    createReview: async (
        skillId: string,
        data: SkillReviewCreate
    ): Promise<SuccessResponse<SkillReview>> => {
        const response = await apiClient.post(`/marketplace/skills/${skillId}/reviews`, data);
        return response.data;
    },

    /**
     * Mark review as helpful
     */
    markReviewHelpful: async (reviewId: string): Promise<void> => {
        await apiClient.post(`/marketplace/reviews/${reviewId}/helpful`);
    },
};

// ==================== Marketplace Items (Templates, Themes) ====================

export interface MarketplaceItem {
    id: string;
    seller_id: string;
    seller_name?: string;
    type: string; // template, theme, course, feature, emoji_pack
    category?: string;
    name: string;
    description?: string;
    short_description?: string;
    price: number;
    currency: string;
    source_type?: string;
    icon_url?: string;
    cover_image_url?: string;
    screenshots?: string[];
    install_count: number;
    rating_avg: number;
    rating_count: number;
    is_featured: boolean;
    is_installed?: boolean;
    version: string;
    tags?: string[];
    status?: string;
    created_at?: string;
    updated_at?: string;
}

export interface MarketplaceInstallation {
    installation_id: string;
    item_id: string;
    item_name: string;
    item_type?: string;
    cloned_resource_type?: string;
    cloned_resource_id?: string;
    installed_at?: string;
}

export interface MarketplaceItemReview {
    id: string;
    user_id: string;
    user_name: string;
    rating: number;
    comment?: string;
    created_at?: string;
}

export interface BrowseItemsParams {
    type?: string;
    category?: string;
    search?: string;
    featured?: boolean;
    page?: number;
    page_size?: number;
}

const marketplaceItemService = {
    browseItems: async (params?: BrowseItemsParams): Promise<PaginatedResponse<MarketplaceItem>> => {
        const response = await apiClient.get("/marketplace/items", { params });
        return response.data;
    },

    getItemDetail: async (itemId: string) => {
        const response = await apiClient.get(`/marketplace/items/${itemId}`);
        return response.data;
    },

    installItem: async (itemId: string) => {
        const response = await apiClient.post(`/marketplace/items/${itemId}/install`);
        return response.data;
    },

    uninstallItem: async (itemId: string) => {
        const response = await apiClient.delete(`/marketplace/items/${itemId}/uninstall`);
        return response.data;
    },

    getMyInstallations: async (params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<MarketplaceInstallation>> => {
        const response = await apiClient.get("/marketplace/my-installations", { params });
        return response.data;
    },

    getItemReviews: async (itemId: string, params?: { page?: number; page_size?: number }) => {
        const response = await apiClient.get(`/marketplace/items/${itemId}/reviews`, { params });
        return response.data;
    },

    addReview: async (itemId: string, rating: number, comment?: string) => {
        const response = await apiClient.post(`/marketplace/items/${itemId}/reviews`, null, {
            params: { rating, comment },
        });
        return response.data;
    },

    createItem: async (params: {
        name: string;
        type: string;
        source_type: string;
        source_id: string;
        description?: string;
        short_description?: string;
        category?: string;
        price?: number;
    }) => {
        const response = await apiClient.post("/marketplace/items", null, { params });
        return response.data;
    },

    submitForReview: async (itemId: string) => {
        const response = await apiClient.put(`/marketplace/items/${itemId}/submit`);
        return response.data;
    },

    approveItem: async (itemId: string) => {
        const response = await apiClient.put(`/marketplace/items/${itemId}/approve`);
        return response.data;
    },
};

export { marketplaceItemService };
export default marketplaceService;
