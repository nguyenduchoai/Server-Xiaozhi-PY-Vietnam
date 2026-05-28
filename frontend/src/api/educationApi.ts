import axiosInstance from "@/config/axios-instance";

export interface EduLessonInput {
    title: string;
    description?: string;
    lesson_order?: number;
    lesson_type?: string;
    content?: Record<string, any>;
    duration_minutes?: number;
    is_published?: boolean;
}

export interface EduCourseInput {
    name: string;
    description?: string;
    cover_image?: string;
    target_audience?: string;
    difficulty?: string;
    estimated_hours?: number;
    price?: number;
    original_price?: number;
    is_published?: boolean;
    lessons?: EduLessonInput[];
}

export const educationApi = {
    listCourses: async (includeUnpublished = true) => {
        const res = await axiosInstance.get("/education/courses", {
            params: { include_unpublished: includeUnpublished },
        });
        return res.data;
    },

    getCourse: async (courseId: string) => {
        const res = await axiosInstance.get(`/education/courses/${courseId}`);
        return res.data;
    },

    createCourse: async (payload: EduCourseInput) => {
        const res = await axiosInstance.post("/education/courses", payload);
        return res.data;
    },

    updateCourse: async (courseId: string, payload: Partial<EduCourseInput>) => {
        const res = await axiosInstance.put(`/education/courses/${courseId}`, payload);
        return res.data;
    },

    deleteCourse: async (courseId: string) => {
        await axiosInstance.delete(`/education/courses/${courseId}`);
    },

    createLesson: async (courseId: string, payload: EduLessonInput) => {
        const res = await axiosInstance.post(`/education/courses/${courseId}/lessons`, payload);
        return res.data;
    },

    updateLesson: async (lessonId: string, payload: Partial<EduLessonInput>) => {
        const res = await axiosInstance.put(`/education/lessons/${lessonId}`, payload);
        return res.data;
    },

    deleteLesson: async (lessonId: string) => {
        const res = await axiosInstance.delete(`/education/lessons/${lessonId}`);
        return res.data;
    },

    reportOverview: async (params?: Record<string, any>) => {
        const res = await axiosInstance.get("/education/reports/overview", { params });
        return res.data;
    },

    reportCourses: async (params?: Record<string, any>) => {
        const res = await axiosInstance.get("/education/reports/courses", { params });
        return res.data;
    },

    reportActivity: async (params?: Record<string, any>) => {
        const res = await axiosInstance.get("/education/reports/activity", { params });
        return res.data;
    },

    getCourseLessons: async (courseId: string, page = 1, limit = 50) => {
        const res = await axiosInstance.get(`/education/courses/${courseId}/lessons`, { params: { page, limit } });
        return res.data;
    },

    purchaseCourse: async (courseId: string) => {
        const res = await axiosInstance.post(`/education/courses/${courseId}/purchase`);
        return res.data;
    },

    reportCourseDetail: async (courseId: string, params?: Record<string, any>) => {
        const res = await axiosInstance.get(`/education/courses/${courseId}/report`, { params });
        return res.data;
    },
};

export default educationApi;
