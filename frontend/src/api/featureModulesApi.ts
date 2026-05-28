/**
 * Feature Modules API Client
 * 
 * Manages: Sales Programs, Meeting Rooms, Agent Feature Toggles
 */

import axiosInstance from '../config/axios-instance';

// ============================================================
// Types
// ============================================================

export interface SalesProgram {
    id: string;
    user_id: string;
    name: string;
    description?: string;
    mode: string;
    system_prompt?: string;
    knowledge_base_id?: string;
    welcome_message?: string;
    business_name?: string;
    business_address?: string;
    business_phone?: string;
    display_config?: Record<string, any>;
    is_active: boolean;
}

export interface SalesProgramCreate {
    name: string;
    description?: string;
    mode?: string;
    system_prompt?: string;
    knowledge_base_id?: string;
    welcome_message?: string;
    business_name?: string;
    business_address?: string;
    business_phone?: string;
    display_config?: Record<string, any>;
}

export interface MeetingRoom {
    id: string;
    user_id: string;
    name: string;
    department?: string;
    description?: string;
    default_language: string;
    auto_extract_tasks: boolean;
    auto_summarize: boolean;
    notification_config?: Record<string, any>;
    members?: Array<Record<string, any>>;
    is_active: boolean;
}

export interface MeetingRoomCreate {
    name: string;
    department?: string;
    description?: string;
    default_language?: string;
    auto_extract_tasks?: boolean;
    auto_summarize?: boolean;
    notification_config?: Record<string, any>;
    members?: Array<Record<string, any>>;
}

export interface EducationCourse {
    id: string;
    user_id: string;
    name: string;
    description?: string;
    difficulty?: string;
    estimated_hours?: number;
    is_published: boolean;
}

export interface AgentFeatures {
    agent_id: string;
    enable_education: boolean;
    enable_sales: boolean;
    enable_meeting: boolean;
    enable_knowledge_base: boolean;
    enable_memory: boolean;
    course_ids: string[];
    sales_program_ids: string[];
    meeting_room_ids: string[];
    knowledge_base_ids: string[];
    // Subscription plan gating
    plan_allowed: Record<string, boolean>;
    plan_name: string;
}

export interface AgentFeaturesUpdate {
    enable_education?: boolean;
    enable_sales?: boolean;
    enable_meeting?: boolean;
    enable_knowledge_base?: boolean;
    enable_memory?: boolean;
    course_ids?: string[];
    sales_program_ids?: string[];
    meeting_room_ids?: string[];
    knowledge_base_ids?: string[];
}

// ============================================================
// API Functions
// ============================================================

export const featureModulesApi = {
    // --- Sales Programs ---
    getSalesPrograms: async (): Promise<SalesProgram[]> => {
        const res = await axiosInstance.get('/features/sales-programs');
        return res.data;
    },

    createSalesProgram: async (data: SalesProgramCreate): Promise<SalesProgram> => {
        const res = await axiosInstance.post('/features/sales-programs', data);
        return res.data;
    },

    updateSalesProgram: async (id: string, data: Partial<SalesProgramCreate>): Promise<SalesProgram> => {
        const res = await axiosInstance.put(`/features/sales-programs/${id}`, data);
        return res.data;
    },

    deleteSalesProgram: async (id: string): Promise<void> => {
        await axiosInstance.delete(`/features/sales-programs/${id}`);
    },

    // --- Meeting Rooms ---
    getMeetingRooms: async (): Promise<MeetingRoom[]> => {
        const res = await axiosInstance.get('/features/meeting-rooms');
        return res.data;
    },

    createMeetingRoom: async (data: MeetingRoomCreate): Promise<MeetingRoom> => {
        const res = await axiosInstance.post('/features/meeting-rooms', data);
        return res.data;
    },

    updateMeetingRoom: async (id: string, data: Partial<MeetingRoomCreate>): Promise<MeetingRoom> => {
        const res = await axiosInstance.put(`/features/meeting-rooms/${id}`, data);
        return res.data;
    },

    deleteMeetingRoom: async (id: string): Promise<void> => {
        await axiosInstance.delete(`/features/meeting-rooms/${id}`);
    },

    // --- Education Courses ---
    getEducationCourses: async (includeUnpublished = true): Promise<EducationCourse[]> => {
        const res = await axiosInstance.get('/education/courses', {
            params: { include_unpublished: includeUnpublished },
        });
        return res.data?.items || [];
    },

    // --- Agent Feature Toggles ---
    getAgentFeatures: async (agentId: string): Promise<AgentFeatures> => {
        const res = await axiosInstance.get(`/features/agents/${agentId}`);
        return res.data;
    },

    updateAgentFeatures: async (agentId: string, data: AgentFeaturesUpdate): Promise<AgentFeatures> => {
        const res = await axiosInstance.patch(`/features/agents/${agentId}`, data);
        return res.data;
    },
};

export default featureModulesApi;
