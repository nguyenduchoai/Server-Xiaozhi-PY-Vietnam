/**
 * News Service - API client for news reading
 */
import apiClient from "@/config/axios-instance";

// ==================== Types ====================

export interface NewsArticle {
    index: number;
    title: string;
    description?: string;
    link: string;
    pub_date?: string;
    image_url?: string;
}

export interface NewsListResponse {
    success: boolean;
    source: string;
    topic: string;
    total: number;
    articles: NewsArticle[];
}

export interface ArticleDetailResponse {
    success: boolean;
    title: string;
    link: string;
    content: string;  // Markdown
    pub_date?: string;
    source: string;
}

export interface SummaryResponse {
    success: boolean;
    article_url: string;
    summary: string;
}

export interface TopicInfo {
    name: string;
    path: string;
}

export interface SourceInfo {
    name: string;
    base_url: string;
    topics: TopicInfo[];
}

// ==================== Service ====================

const newsService = {
    /**
     * Lấy danh sách tin tức theo chủ đề
     */
    getNewsList: async (params: {
        source?: string;
        topic: string;
        max_articles?: number;
    }): Promise<NewsListResponse> => {
        const response = await apiClient.post('/news/list', {
            source: params.source || 'vnexpress',
            topic: params.topic,
            max_articles: params.max_articles || 10,
        });
        return response.data;
    },

    /**
     * Lấy nội dung chi tiết bài viết
     */
    getArticleDetail: async (params: {
        url: string;
        source?: string;
    }): Promise<ArticleDetailResponse> => {
        const response = await apiClient.post('/news/detail', {
            url: params.url,
            source: params.source || 'vnexpress',
        });
        return response.data;
    },

    /**
     * Tóm tắt bài viết bằng AI
     */
    summarizeArticle: async (params: {
        url: string;
        source?: string;
    }): Promise<SummaryResponse> => {
        const response = await apiClient.post('/news/summarize', {
            url: params.url,
            source: params.source || 'vnexpress',
        });
        return response.data;
    },

    /**
     * Lấy danh sách nguồn tin
     */
    getSources: async (): Promise<{ success: boolean; sources: SourceInfo[] }> => {
        const response = await apiClient.get('/news/sources');
        return response.data;
    },

    /**
     * Lấy danh sách topics của một nguồn
     */
    getTopics: async (source: string = 'vnexpress'): Promise<{ success: boolean; source: string; topics: TopicInfo[] }> => {
        const response = await apiClient.get(`/news/topics`, {
            params: { source }
        });
        return response.data;
    },
};

export default newsService;
