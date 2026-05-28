/**
 * Xiaozhi CE (Community Edition) - App Router
 * Core features only: Agents, Devices, OTA, Firmware, Assets, Providers
 */
import { Routes, Route, Outlet, Link } from "react-router-dom";
import { Wand2, Download } from "lucide-react";
import {
  LoginPage,
  ChatPage,
  ProfilePage,
  SettingsPage,
  NotFoundPage,
  AgentsPage,
  AgentDetailPage,
  AgentKnowledgePageV2,
  AgentMemoryPage,
  AgentHistoryPage,
  DevicesPage,
  DeviceDetailPage,
  DeviceCustomizePage,
  DisplayCustomizerPage,
  ProvidersPage,
  ToolsPage,
  TemplatesPage,
  TemplateDetailPage,
  TemplateEditPage,
  McpConfigsPage,
  FirmwareFlasherPage,
  FirmwareManagementPage,
  McpEndpointPage,
  AssetTemplatesPage,
  AssetGeneratorPage,
  MemoryPage,
  MarketplacePage,
  EmojiPackPage,
  EmojiPackEditorPage,
} from "@/pages";
import NotificationsPage from "@/pages/NotificationsPage";
import HomePage from "@/pages/HomePage";
import DashboardPage from "@/pages/DashboardPage";
import TermsPage from "@/pages/TermsPage";
import PrivacyPage from "@/pages/PrivacyPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import AdminUsersPage from "@/pages/admin/AdminUsersPage";
import AdminPlansPage from "@/pages/admin/AdminPlansPage";
import AdminHardwareTypesPage from "@/pages/admin/AdminHardwareTypesPage";
import AdminSystemHealthPage from "@/pages/admin/AdminSystemHealthPage";
import AdminSystemSettingsPage from "@/pages/admin/AdminSystemSettingsPage";
import AdminDevicesPage from "@/pages/admin/AdminDevicesPage";
import ThemeGalleryPage from "@/pages/ThemeGalleryPage";
import KnowledgeBasePage from "@/pages/KnowledgeBasePage";
import KnowledgeBaseDetailPage from "@/pages/KnowledgeBaseDetailPage";
import RegisterPage from "@/pages/RegisterPage";
import OTADashboardPage from "@/pages/OTADashboardPage";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminRoute } from "@/components/AdminRoute";
import { SemiLayout } from "@/layouts";
import { OnboardingWizard } from "@/components/OnboardingWizard";


// Layout for protected routes
const ProtectedLayout = () => (
  <SemiLayout>
    <Outlet />
    <OnboardingWizard />
  </SemiLayout>
);

// Layout for public routes with minimal top bar
const PublicLayout = () => (
  <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
    <header className="sticky top-0 z-50 bg-white/70 backdrop-blur-xl border-b border-slate-200 shadow-sm transition-all">
      <div className="container mx-auto px-4 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
              <Link to="/" className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-violet-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-bold shadow-md shadow-violet-500/20">X</div>
                  <span className="text-xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">XiaoZhi AI IoT</span>
              </Link>
          </div>

          <nav className="hidden lg:flex items-center gap-8">
              <Link to="/#features" className="text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">Tính năng</Link>
              <Link to="/#installation" className="text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">Triển khai</Link>
              <Link to="/#faq" className="text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">Hỏi đáp</Link>
              
              <span className="w-px h-5 bg-slate-200"></span>

              <Link to="/asset-generator" className="flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">
                  <Wand2 className="w-3.5 h-3.5" />Assets
              </Link>
              <Link to="/tools/flasher" className="flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">
                  <Download className="w-3.5 h-3.5" />Flasher
              </Link>
          </nav>

          <div className="flex items-center gap-4">
              <Link to="/login" className="hidden sm:block">
                  <button className="h-10 px-4 py-2 inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-slate-600 hover:text-violet-700 hover:bg-violet-50">Đăng nhập</button>
              </Link>
              <Link to="/login">
              <button className="h-10 inline-flex items-center justify-center whitespace-nowrap font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 rounded-full px-6 shadow-md shadow-violet-600/20 border border-violet-500/50">
                  Bắt đầu tạo AI
              </button>
              </Link>
          </div>
      </div>
    </header>
    <main className="flex-1 overflow-auto">
      <Outlet />
    </main>
  </div>
);


function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/terms" element={<TermsPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Public tools routes with UI shell */}
      <Route element={<PublicLayout />}>
        <Route path="/tools/flasher" element={<FirmwareFlasherPage />} />
        <Route path="/asset-generator" element={<AssetGeneratorPage />} />
      </Route>

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <ProtectedLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/agents/:agentId" element={<AgentDetailPage />} />
        <Route path="/agents/:agentId/knowledge" element={<AgentKnowledgePageV2 />} />
        <Route path="/agents/:agentId/memory" element={<AgentMemoryPage />} />
        <Route path="/agents/:agentId/history" element={<AgentHistoryPage />} />
        <Route path="/devices" element={<DevicesPage />} />
        <Route path="/devices/:deviceId" element={<DeviceDetailPage />} />
        <Route path="/devices/:deviceId/customize" element={<DeviceCustomizePage />} />
        <Route path="/display-customizer" element={<DisplayCustomizerPage />} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/firmware" element={<FirmwareManagementPage />} />
        <Route path="/ota-dashboard" element={<OTADashboardPage />} />

        <Route path="/asset-templates" element={<AssetTemplatesPage />} />
        <Route path="/providers" element={<ProvidersPage />} />
        <Route path="/memory" element={<MemoryPage />} />
        <Route path="/knowledge" element={<KnowledgeBasePage />} />
        <Route path="/knowledge/:id" element={<KnowledgeBaseDetailPage />} />
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route path="/themes" element={<ThemeGalleryPage />} />

        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/emoji-packs" element={<EmojiPackPage />} />
        <Route path="/emoji-packs/:packId/edit" element={<EmojiPackEditorPage />} />
        <Route path="/emoji-packs/new" element={<EmojiPackEditorPage />} />
        <Route path="/mcp-configs" element={<McpConfigsPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/templates/:templateId" element={<TemplateDetailPage />} />
        <Route path="/templates/:templateId/edit" element={<TemplateEditPage />} />

        {/* Admin routes */}
        <Route path="/admin/plans" element={<AdminRoute><AdminPlansPage /></AdminRoute>} />
        <Route path="/admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
        <Route path="/admin/hardware-types" element={<AdminRoute><AdminHardwareTypesPage /></AdminRoute>} />
        <Route path="/admin/mcp-endpoint" element={<AdminRoute><McpEndpointPage /></AdminRoute>} />
        <Route path="/admin/system-health" element={<AdminRoute><AdminSystemHealthPage /></AdminRoute>} />
        <Route path="/admin/system-settings" element={<AdminRoute><AdminSystemSettingsPage /></AdminRoute>} />
        <Route path="/admin/devices" element={<AdminRoute><AdminDevicesPage /></AdminRoute>} />

        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<AdminRoute><SettingsPage /></AdminRoute>} />
        <Route path="/settings/integrations" element={<AdminRoute><SettingsPage section="integrations" /></AdminRoute>} />
      </Route>

      {/* 404 fallback */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default App;
