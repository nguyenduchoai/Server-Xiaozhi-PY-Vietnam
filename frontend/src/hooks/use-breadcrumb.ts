import { useLocation, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

export interface BreadcrumbItem {
  label: string;
  href?: string;
  isActive: boolean;
}

interface BreadcrumbParams {
  agentName?: string;
  templateName?: string;
}

/**
 * Hook to generate breadcrumb items from current route
 * Maps route paths to user-friendly labels using i18n
 * NOW covers ALL routes in the application
 *
 * @param params - Optional params with agentName/templateName to display in breadcrumb
 */
export function useBreadcrumb(params?: BreadcrumbParams): BreadcrumbItem[] {
  const location = useLocation();
  const routeParams = useParams();
  const { t } = useTranslation("navigation");

  // Complete route label mapping — covers every page in the app
  const routeLabels: Record<string, string> = {
    // Core
    dashboard: "Dashboard",
    chat: t("breadcrumb.chat", "Chat"),
    agents: t("breadcrumb.agents", "Agents"),
    templates: t("breadcrumb.templates", "Templates"),
    devices: t("breadcrumb.devices", "Thiết bị"),
    profile: t("breadcrumb.profile", "Hồ sơ"),
    settings: t("breadcrumb.settings", "Cài đặt"),

    // AI Config
    providers: "Providers",
    tools: "Công cụ",
    "mcp-configs": "MCP Configs",

    // Devices & OTA
    "ota-dashboard": "OTA Dashboard",
    firmware: "Firmware",
    flasher: "Web Flasher",
    "asset-templates": "Asset Templates",
    "asset-generator": "Asset Generator",
    "display-customizer": "Display Customizer",
    themes: "Kho Theme",

    // Knowledge
    memory: "Bộ nhớ",
    knowledge: "Kho Tri Thức",

    // Voice
    voices: "Thư viện Giọng nói",
    voiceprint: "Nhận diện Giọng",

    // Features
    education: "Học Tập",
    meetings: "Cuộc Họp",
    friends: "Bạn Bè",

    // Communication
    notifications: "Thông Báo",

    // Account
    subscription: "Gói đăng ký",
    marketplace: "Marketplace",
    licenses: "License & Features",
    "emoji-packs": "Emoji Packs",

    // Education sub-routes
    courses: "Khóa học",
    lessons: "Bài học",
    flashcards: "Flashcards",
    quizzes: "Bài kiểm tra",
    leaderboard: "Bảng xếp hạng",
    generate: "AI Course Generator",
    create: "Tạo mới",
    edit: "Chỉnh sửa",
    review: "Ôn tập",

    // Meeting sub-routes
    // 'settings' already mapped

    // Payment
    payment: "Thanh toán",
    result: "Kết quả",

    // Admin
    admin: "Quản trị",
    users: "Người dùng",
    plans: "Gói cước",
    payments: "Thanh toán",
    "hardware-types": "Loại phần cứng",
    "mcp-endpoint": "MCP Endpoint",
    "system-health": "Sức khỏe Hệ thống",
  };

  // Split the path and filter empty segments
  const pathSegments = location.pathname
    .split("/")
    .filter((segment) => segment !== "");

  // Build breadcrumb items
  const breadcrumbs: BreadcrumbItem[] = [
    {
      label: t("breadcrumb.home", "Trang chủ"),
      href: "/dashboard",
      isActive: location.pathname === "/" || location.pathname === "/dashboard",
    },
  ];

  // Track already processed segments (for ID-based routes like /agents/:agentId)
  const processed = new Set<number>();

  // Process each path segment
  pathSegments.forEach((segment, index) => {
    if (processed.has(index)) return;

    const isLast = index === pathSegments.length - 1;
    const href = `/${pathSegments.slice(0, index + 1).join("/")}`;

    // Handle agent detail routes
    if (segment === "agents" && routeParams.agentId) {
      breadcrumbs.push({
        label: t("breadcrumb.agents", "Agents"),
        href: "/agents",
        isActive: false,
      });
      // Mark the agentId segment as processed
      const agentIdIndex = pathSegments.indexOf(routeParams.agentId);
      if (agentIdIndex > -1) processed.add(agentIdIndex);

      breadcrumbs.push({
        label: params?.agentName || `Agent`,
        href: `/agents/${routeParams.agentId}`,
        isActive: agentIdIndex === pathSegments.length - 1,
      });

      // Handle sub-routes like /agents/:id/knowledge  
      const subRoute = pathSegments[agentIdIndex + 1];
      if (subRoute) {
        processed.add(agentIdIndex + 1);
        breadcrumbs.push({
          label: routeLabels[subRoute] || subRoute,
          isActive: true,
        });
      }
      return;
    }

    // Handle template detail routes
    if (segment === "templates" && routeParams.templateId) {
      breadcrumbs.push({
        label: t("breadcrumb.templates", "Templates"),
        href: "/templates",
        isActive: false,
      });
      const templateIdIndex = pathSegments.indexOf(routeParams.templateId);
      if (templateIdIndex > -1) processed.add(templateIdIndex);

      breadcrumbs.push({
        label: params?.templateName || "Template",
        isActive: templateIdIndex === pathSegments.length - 1,
      });

      const subRoute = pathSegments[templateIdIndex + 1];
      if (subRoute) {
        processed.add(templateIdIndex + 1);
        breadcrumbs.push({
          label: routeLabels[subRoute] || subRoute,
          isActive: true,
        });
      }
      return;
    }

    // Skip UUIDs and numeric IDs
    if (isUUID(segment) || /^\d+$/.test(segment)) {
      return;
    }

    // Standard route segment
    if (routeLabels[segment]) {
      breadcrumbs.push({
        label: routeLabels[segment],
        href: isLast ? undefined : href,
        isActive: isLast,
      });
    } else {
      // Fallback: capitalize segment name
      breadcrumbs.push({
        label: segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' '),
        href: isLast ? undefined : href,
        isActive: isLast,
      });
    }
  });

  return breadcrumbs;
}

// Helper to detect UUID segments
function isUUID(str: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str);
}
