/**
 * User Role Types
 * Matches backend UserRole enum
 */
export const UserRole = {
    USER: "user",
    ADMIN: "admin",
    SUPER_ADMIN: "super_admin",
} as const;

export type UserRole = typeof UserRole[keyof typeof UserRole];

/**
 * User role labels for display
 */
export const UserRoleLabels: Record<UserRole, string> = {
    [UserRole.USER]: "Người dùng",
    [UserRole.ADMIN]: "Quản trị viên",
    [UserRole.SUPER_ADMIN]: "Quản trị cấp cao",
};

/**
 * User role descriptions
 */
export const UserRoleDescriptions: Record<UserRole, string> = {
    [UserRole.USER]: "Quyền truy cập cơ bản",
    [UserRole.ADMIN]: "Quản lý người dùng và dữ liệu",
    [UserRole.SUPER_ADMIN]: "Toàn quyền quản trị hệ thống",
};
