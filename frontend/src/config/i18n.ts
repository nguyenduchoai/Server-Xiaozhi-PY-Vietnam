import i18next from "i18next";
import { initReactI18next } from "react-i18next";

// Import translation resources
import authEn from "@/locales/en/auth.json";
import authVi from "@/locales/vi/auth.json";
import chatEn from "@/locales/en/chat.json";
import chatVi from "@/locales/vi/chat.json";
import navigationEn from "@/locales/en/navigation.json";
import navigationVi from "@/locales/vi/navigation.json";
import commonEn from "@/locales/en/common.json";
import commonVi from "@/locales/vi/common.json";
import agentsEn from "@/locales/en/agents.json";
import agentsVi from "@/locales/vi/agents.json";
import templatesEn from "@/locales/en/templates.json";
import templatesVi from "@/locales/vi/templates.json";
import devicesEn from "@/locales/en/devices.json";
import devicesVi from "@/locales/vi/devices.json";
import providersEn from "@/locales/en/providers.json";
import providersVi from "@/locales/vi/providers.json";
import toolsEn from "@/locales/en/tools.json";
import toolsVi from "@/locales/vi/tools.json";
import mcpConfigsEn from "@/locales/en/mcp-configs.json";
import mcpConfigsVi from "@/locales/vi/mcp-configs.json";
import profileEn from "@/locales/en/profile.json";
import profileVi from "@/locales/vi/profile.json";
import newsEn from "@/locales/en/news.json";
import newsVi from "@/locales/vi/news.json";
import memoryEn from "@/locales/en/memory.json";
import memoryVi from "@/locales/vi/memory.json";
import voiceEn from "@/locales/en/voice.json";
import voiceVi from "@/locales/vi/voice.json";
import emojiEn from "@/locales/en/emoji.json";
import emojiVi from "@/locales/vi/emoji.json";
import voiceprintEn from "@/locales/en/voiceprint.json";
import voiceprintVi from "@/locales/vi/voiceprint.json";

import meetingsEn from "@/locales/en/meetings.json";
import meetingsVi from "@/locales/vi/meetings.json";
import adminEn from "@/locales/en/admin.json";
import adminVi from "@/locales/vi/admin.json";
import knowledgeEn from "@/locales/en/knowledge.json";
import knowledgeVi from "@/locales/vi/knowledge.json";
import marketplaceEn from "@/locales/en/marketplace.json";
import marketplaceVi from "@/locales/vi/marketplace.json";
import subscriptionEn from "@/locales/en/subscription.json";
import subscriptionVi from "@/locales/vi/subscription.json";
import notificationsEn from "@/locales/en/notifications.json";
import notificationsVi from "@/locales/vi/notifications.json";
import educationEn from "@/locales/en/education.json";
import educationVi from "@/locales/vi/education.json";

const resources = {
  en: {
    auth: authEn,
    chat: chatEn,
    navigation: navigationEn,
    common: commonEn,
    agents: agentsEn,
    templates: templatesEn,
    devices: devicesEn,
    providers: providersEn,
    tools: toolsEn,
    "mcp-configs": mcpConfigsEn,
    profile: profileEn,
    news: newsEn,
    memory: memoryEn,
    voice: voiceEn,
    emoji: emojiEn,
    voiceprint: voiceprintEn,

    meetings: meetingsEn,
    admin: adminEn,
    knowledge: knowledgeEn,
    marketplace: marketplaceEn,
    subscription: subscriptionEn,
    notifications: notificationsEn,
    education: educationEn,
  },
  vi: {
    auth: authVi,
    chat: chatVi,
    navigation: navigationVi,
    common: commonVi,
    agents: agentsVi,
    templates: templatesVi,
    devices: devicesVi,
    providers: providersVi,
    tools: toolsVi,
    "mcp-configs": mcpConfigsVi,
    profile: profileVi,
    news: newsVi,
    memory: memoryVi,
    voice: voiceVi,
    emoji: emojiVi,
    voiceprint: voiceprintVi,

    meetings: meetingsVi,
    admin: adminVi,
    knowledge: knowledgeVi,
    marketplace: marketplaceVi,
    subscription: subscriptionVi,
    notifications: notificationsVi,
    education: educationVi,
  },
};

i18next
  .use(initReactI18next)
  .init({
    resources,
    lng: "vi", // Force Vietnamese
    fallbackLng: "vi",
    ns: ["common"],
    defaultNS: "common",
    interpolation: {
      escapeValue: false,
    },
  });

export default i18next;

