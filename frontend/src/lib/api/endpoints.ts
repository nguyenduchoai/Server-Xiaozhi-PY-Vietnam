/**
 * Centralized API Endpoints
 * Based on AUTH_ENDPOINTS_V2.md documentation
 * NOTE: baseURL in axios config already includes /api/v1, so don't repeat it here
 */

/**
 * Auth Endpoints
 * Base Path: /auth
 */
export const AUTH_ENDPOINTS = {
  // POST /auth/register
  // Body: { name, username, email, password }
  // Response: { id, name, username, email, profile_image_url }
  REGISTER: "/auth/register",

  // POST /auth/login
  // Body: FormData { username, password }
  // Content-Type: application/x-www-form-urlencoded
  // Response: { access_token, token_type }
  // Sets: refresh_token cookie (httpOnly, secure)
  LOGIN: "/auth/login",

  // POST /auth/refresh
  // Cookies: refresh_token
  // Response: { access_token, token_type }
  REFRESH: "/auth/refresh",

  // POST /auth/logout
  // Headers: Authorization: Bearer <access_token>
  // Cookies: refresh_token
  // Response: { message }
  LOGOUT: "/auth/logout",
} as const;

/**
 * User Endpoints
 */
export const USER_ENDPOINTS = {
  // GET /user/me/
  // Headers: Authorization: Bearer <access_token>
  // Response: { id, name, username, email, profile_image_url }
  ME: "/user/me/",

  // PATCH /user/me
  // Headers: Authorization: Bearer <access_token>
  // Body: { name?, email? }
  // Response: { id, name, email, profile_image_url }
  UPDATE_ME: "/user/me",

  // PUT /user/me/password
  // Headers: Authorization: Bearer <access_token>
  // Body: { current_password, new_password }
  // Response: { message }
  CHANGE_PASSWORD: "/user/me/password",

  // POST /user/me/profile-image
  // Headers: Authorization: Bearer <access_token>
  // Content-Type: multipart/form-data
  // Body: FormData with 'file' field
  // Response: { profile_image_url, message }
  UPLOAD_AVATAR: "/user/me/profile-image",

  // DELETE /user/me
  // Headers: Authorization: Bearer <access_token>
  // Response: { message, deleted_at, restore_deadline }
  DELETE_ACCOUNT: "/user/me",

  // GET /user/{username}
  // Response: { id, name, username, email, profile_image_url }
  GET_BY_USERNAME: (username: string) => `/user/${username}`,

  // GET /users?page=1&items_per_page=10
  // Response: { data, total, page, page_size }
  LIST: "/users",
} as const;

/**
 * Chat Endpoints (placeholders for future use)
 */
export const CHAT_ENDPOINTS = {
  // GET /chats
  LIST: "/chats",

  // POST /chats
  CREATE: "/chats",

  // GET /chats/{id}
  GET: (id: string) => `/chats/${id}`,

  // DELETE /chats/{id}
  DELETE: (id: string) => `/chats/${id}`,

  // GET /chats/{chatId}/messages
  GET_MESSAGES: (chatId: string) => `/chats/${chatId}/messages`,

  // POST /chats/{chatId}/messages
  SEND_MESSAGE: (chatId: string) => `/chats/${chatId}/messages`,
} as const;

/**
 * Message Endpoints (placeholders for future use)
 */
export const MESSAGE_ENDPOINTS = {
  // GET /messages
  LIST: "/messages",

  // POST /messages
  CREATE: "/messages",

  // GET /messages/{id}
  GET: (id: string) => `/messages/${id}`,

  // DELETE /messages/{id}
  DELETE: (id: string) => `/messages/${id}`,
} as const;

/**
 * Device Endpoints
 */
export const DEVICE_ENDPOINTS = {
  // GET /user/devices/
  // Headers: Authorization: Bearer <access_token>
  // Query: page, page_size
  LIST: "/user/devices/",

  // GET /user/devices/{device_id}
  // Headers: Authorization: Bearer <access_token>
  DETAIL: (deviceId: string) => `/user/devices/${deviceId}`,

  // POST /devices/activate
  // Headers: Authorization: Bearer <access_token>
  // Body: { code: "123456" }
  ACTIVATE: "/devices/activate",

  // DELETE /devices/{device_id}
  // Headers: Authorization: Bearer <access_token>
  DELETE: (deviceId: string) => `/devices/${deviceId}`,

  // PATCH /devices/{device_id}
  // Headers: Authorization: Bearer <access_token>
  // Body: { device_name?, board?, status? }
  UPDATE: (deviceId: string) => `/devices/${deviceId}`,

  // ── Agent-Device M2M ──
  // GET /devices/{device_id}/agents - List agents assigned to device
  AGENTS: (deviceId: string) => `/devices/${deviceId}/agents`,

  // POST /devices/{device_id}/agents - Assign agent (agent_id in body)
  ASSIGN_AGENT: (deviceId: string) =>
    `/devices/${deviceId}/agents`,

  // DELETE /devices/{device_id}/agents/{agent_id} - Unassign agent
  UNASSIGN_AGENT: (deviceId: string, agentId: string) =>
    `/devices/${deviceId}/agents/${agentId}`,

  // PUT /devices/{device_id}/switch-agent/{agent_id} - Switch active agent
  SWITCH_AGENT: (deviceId: string, agentId: string) =>
    `/devices/${deviceId}/switch-agent/${agentId}`,
} as const;

/**
 * Agent Endpoints
 */
export const AGENT_ENDPOINTS = {
  // GET /agents, POST /agents
  LIST: "/agents",

  // GET /agents/{agent_id}, PUT /agents/{agent_id}, DELETE /agents/{agent_id}
  DETAIL: (agentId: string) => `/agents/${agentId}`,

  // POST /agents/{agent_id}/bind-device
  BIND_DEVICE: (agentId: string) => `/agents/${agentId}/bind-device`,

  // POST /agents/{agent_id}/bind-device-id
  BIND_DEVICE_ID: (agentId: string) => `/agents/${agentId}/bind-device-id`,

  // DELETE /agents/{agent_id}/device
  DELETE_DEVICE: (agentId: string) => `/agents/${agentId}/device`,

  // GET /agents/{agent_id}/templates - List templates assigned to agent
  TEMPLATES: (agentId: string) => `/agents/${agentId}/templates`,

  // POST /agents/{agent_id}/templates/{template_id} - Assign template to agent
  ASSIGN_TEMPLATE: (agentId: string, templateId: string) =>
    `/agents/${agentId}/templates/${templateId}`,

  // DELETE /agents/{agent_id}/templates/{template_id} - Unassign template from agent
  UNASSIGN_TEMPLATE: (agentId: string, templateId: string) =>
    `/agents/${agentId}/templates/${templateId}`,

  // PUT /agents/{agent_id}/activate-template/{template_id} - Activate template for agent
  ACTIVATE_TEMPLATE: (agentId: string, templateId: string) =>
    `/agents/${agentId}/activate-template/${templateId}`,

  // GET /agents/{agent_id}/messages - List messages with pagination
  MESSAGES: (agentId: string) => `/agents/${agentId}/messages`,

  // GET /agents/{agent_id}/messages/sessions - List chat sessions
  MESSAGES_SESSIONS: (agentId: string) =>
    `/agents/${agentId}/messages/sessions`,

  // GET /agents/{agent_id}/messages/{session_id} - Get messages for a specific session
  MESSAGES_SESSION_DETAIL: (agentId: string, sessionId: string) =>
    `/agents/${agentId}/messages/${sessionId}`,

  // DELETE /agents/{agent_id}/messages - Delete messages (with optional session_id)
  DELETE_MESSAGES: (agentId: string) => `/agents/${agentId}/messages`,

  // GET /agents/{agent_id}/chat-history/{message_id}/audio - Replay saved utterance audio
  MESSAGE_AUDIO: (agentId: string, messageId: string) =>
    `/agents/${agentId}/chat-history/${messageId}/audio`,

  // GET /agents/{agent_id}/webhook-config - Get webhook configuration
  // POST /agents/{agent_id}/webhook-config - Create/Generate webhook API key
  // DELETE /agents/{agent_id}/webhook-config - Delete webhook API key
  WEBHOOK_CONFIG: (agentId: string) => `/agents/${agentId}/webhook-config`,

  // POST /agents/{agent_id}/webhook - Webhook endpoint
  WEBHOOK: (agentId: string) => `/agents/${agentId}/webhook`,
} as const;

/**
 * Template Endpoints (Independent Template API)
 * Base Path: /templates
 */
export const TEMPLATE_ENDPOINTS = {
  // GET /templates - List templates (supports include_public query param)
  // POST /templates - Create new template
  LIST: "/templates",

  // GET /templates/{template_id}
  // PUT /templates/{template_id}
  // DELETE /templates/{template_id}
  DETAIL: (templateId: string) => `/templates/${templateId}`,

  // GET /templates/{template_id}/agents - List agents using this template
  AGENTS: (templateId: string) => `/templates/${templateId}/agents`,

  // POST /templates/{template_id}/agents/{agent_id} - Assign template to agent (from template side)
  ASSIGN_AGENT: (templateId: string, agentId: string) =>
    `/templates/${templateId}/agents/${agentId}`,

  // DELETE /templates/{template_id}/agents/{agent_id} - Unassign template from agent (from template side)
  UNASSIGN_AGENT: (templateId: string, agentId: string) =>
    `/templates/${templateId}/agents/${agentId}`,
} as const;

/**
 * Provider Endpoints
 * Base Path: /providers
 */
export const PROVIDER_ENDPOINTS = {
  // GET /providers - Lấy danh sách providers
  // POST /providers - Tạo provider mới
  LIST: "/providers",

  // GET /providers/{provider_id}
  // PUT /providers/{provider_id}
  // DELETE /providers/{provider_id}
  DETAIL: (providerId: string) => `/providers/${providerId}`,

  // GET /providers/schemas - Lấy tất cả schemas (không cần auth)
  SCHEMAS: "/providers/schemas",

  // GET /providers/schemas/categories - Lấy categories kèm schema (không cần auth)
  SCHEMA_CATEGORIES: "/providers/schemas/categories",

  // GET /providers/models/{provider_type} - Load models từ provider API
  MODELS: (providerType: string) => `/providers/models/${providerType}`,

  // GET /providers/voices/{provider_type} - Load voices từ TTS provider API
  VOICES: (providerType: string) => `/providers/voices/${providerType}`,

  // POST /providers/validate - Validate config
  VALIDATE: "/providers/validate",

  // POST /providers/test - Test connection
  TEST: "/providers/test",

  // GET /providers/config/modules - Lấy danh sách modules theo category
  CONFIG_MODULES: "/providers/config/modules",

  // POST /providers/validate-reference - Validate provider reference format
  VALIDATE_REFERENCE: "/providers/validate-reference",

  // POST /providers/test-reference - Test provider by reference string
  TEST_REFERENCE: "/providers/test-reference",
} as const;

/**
 * Reminder Endpoints
 */
export const REMINDER_ENDPOINTS = {
  // GET /agents/{agent_id}/reminders
  // POST /agents/{agent_id}/reminders
  LIST: (agentId: string) => `/agents/${agentId}/reminders`,

  // GET /reminders/{reminder_id}
  // PATCH /reminders/{reminder_id}
  // DELETE /reminders/{reminder_id}
  DETAIL: (reminderId: string) => `/reminders/${reminderId}`,

  // POST /reminders/{reminder_id}/received
  MARK_RECEIVED: (reminderId: string) => `/reminders/${reminderId}/received`,
} as const;

/**
 * Tool Endpoints (v2.0)
 * Base Path: /tools
 * Note: UserTool CRUD endpoints removed in v2.0 - only system functions available
 */
export const TOOL_ENDPOINTS = {
  // GET /tools/available - Lấy danh sách system functions có sẵn
  AVAILABLE: "/tools/available",

  // GET /tools/options - Lấy tool options cho dropdown (cần auth)
  OPTIONS: "/tools/options",
} as const;

/**
 * MCP Configuration Endpoints
 * Base Path: /users/me/mcp-configs
 */
export const MCP_ENDPOINTS = {
  // GET /users/me/mcp-configs - List MCP configurations
  // POST /users/me/mcp-configs - Create new MCP configuration
  LIST: "/users/me/mcp-configs",

  // GET /users/me/mcp-configs/{config_id}
  // PUT /users/me/mcp-configs/{config_id}
  // DELETE /users/me/mcp-configs/{config_id}
  DETAIL: (configId: string) => `/users/me/mcp-configs/${configId}`,

  // POST /users/me/mcp-configs/{config_id}/test
  TEST: (configId: string) => `/users/me/mcp-configs/${configId}/test`,

  // POST /users/me/mcp-configs/test-raw - Test config before saving
  TEST_RAW: "/users/me/mcp-configs/test-raw",

  // POST /users/me/mcp-configs/{config_id}/refresh-tools - Refresh tools from MCP server
  REFRESH_TOOLS: (configId: string) =>
    `/users/me/mcp-configs/${configId}/refresh-tools`,
} as const;

/**
 * Agent MCP Selection Endpoints (Refactored from Tool Selection)
 * Base Path: /agents
 */
export const AGENT_MCP_ENDPOINTS = {
  // GET /agents/{agent_id}/mcp
  // PUT /agents/{agent_id}/mcp
  SELECTION: (agentId: string) => `/agents/${agentId}/mcp`,

  // GET /agents/{agent_id}/mcp/available?source=all|user|config
  AVAILABLE_SERVERS: (agentId: string) => `/agents/${agentId}/mcp/available`,
} as const;

/**
 * @deprecated Use AGENT_MCP_ENDPOINTS instead
 */
export const AGENT_TOOL_ENDPOINTS = {
  // GET /agents/{agent_id}/tools
  // PUT /agents/{agent_id}/tools
  SELECTION: (agentId: string) => `/agents/${agentId}/tools`,

  // GET /agents/{agent_id}/tools/available/mcp
  AVAILABLE_MCP_TOOLS: (agentId: string) =>
    `/agents/${agentId}/tools/available/mcp`,

  // GET /agents/{agent_id}/tools/available/plugin
  AVAILABLE_PLUGIN_TOOLS: (agentId: string) =>
    `/agents/${agentId}/tools/available/plugin`,
} as const;

/**
 * Plugin Management Endpoints
 * Base Path: /tools/plugins
 */
export const PLUGIN_ENDPOINTS = {
  // GET /tools/plugins - List plugins
  LIST: "/tools/plugins",

  // GET /tools/plugins/{plugin_name}
  DETAIL: (pluginName: string) => `/tools/plugins/${pluginName}`,

  // POST /tools/plugins/{plugin_name}/test
  TEST: (pluginName: string) => `/tools/plugins/${pluginName}/test`,

  // POST /tools/plugins/{plugin_name}/validate
  VALIDATE: (pluginName: string) => `/tools/plugins/${pluginName}/validate`,

  // GET /tools/plugins/categories/list
  CATEGORIES: "/tools/plugins/categories/list",
} as const;

/**
 * Knowledge Base Endpoints (V1 - OpenMemory - For Personal Memory)
 * @deprecated Use MEMORY_ENDPOINTS instead for personal facts
 * Base Path: /agents/{agent_id}/knowledge-base
 */
export const KNOWLEDGE_BASE_ENDPOINTS = {
  // GET /knowledge-base/health - Check health status
  HEALTH: "/knowledge-base/health",

  // GET /knowledge-base/sectors - Get supported sectors
  SECTORS: "/knowledge-base/sectors",

  // GET /agents/{agent_id}/knowledge-base/items - List entries
  // POST /agents/{agent_id}/knowledge-base/items - Create entry
  ITEMS: (agentId: string) => `/agents/${agentId}/knowledge-base/items`,

  // GET /agents/{agent_id}/knowledge-base/items/{item_id} - Get entry
  // PATCH /agents/{agent_id}/knowledge-base/items/{item_id} - Update entry
  // DELETE /agents/{agent_id}/knowledge-base/items/{item_id} - Delete entry
  ITEM_DETAIL: (agentId: string, itemId: string) =>
    `/agents/${agentId}/knowledge-base/items/${itemId}`,

  // POST /agents/{agent_id}/knowledge-base/search - Semantic search
  SEARCH: (agentId: string) => `/agents/${agentId}/knowledge-base/search`,

  // POST /agents/{agent_id}/knowledge-base/ingest/file - Ingest file
  INGEST_FILE: (agentId: string) =>
    `/agents/${agentId}/knowledge-base/ingest/file`,

  // POST /agents/{agent_id}/knowledge-base/ingest/url - Ingest URL
  INGEST_URL: (agentId: string) =>
    `/agents/${agentId}/knowledge-base/ingest/url`,
} as const;

/**
 * Knowledge Base V2 Endpoints (RAGFlow - For Documents)
 * Base Path: /agents/{agent_id}/knowledge-base (V2 uses same path, different router)
 * Use this for document uploads (PDF, DOCX, etc.)
 */
export const KNOWLEDGE_BASE_V2_ENDPOINTS = {
  // GET /agents/{agent_id}/knowledge-base/health
  HEALTH: (agentId: string) => `/agents/${agentId}/knowledge-base/health`,

  // POST /agents/{agent_id}/knowledge-base/upload - Upload document
  UPLOAD: (agentId: string) => `/agents/${agentId}/knowledge-base/upload`,

  // GET /agents/{agent_id}/knowledge-base/documents - List documents
  DOCUMENTS: (agentId: string) => `/agents/${agentId}/knowledge-base/documents`,

  // DELETE /agents/{agent_id}/knowledge-base/documents/{doc_id}
  DOCUMENT_DETAIL: (agentId: string, docId: string) =>
    `/agents/${agentId}/knowledge-base/documents/${docId}`,

  // POST /agents/{agent_id}/knowledge-base/search - Semantic search
  SEARCH: (agentId: string) => `/agents/${agentId}/knowledge-base/search`,

  // POST /agents/{agent_id}/knowledge-base/text - Upload text content
  TEXT: (agentId: string) => `/agents/${agentId}/knowledge-base/text`,
} as const;

/**
 * Knowledge Base ChromaDB Endpoints (Lightweight Vector DB)
 * Base Path: /agents/{agent_id}/chromadb
 * Use this for text, Excel, and Google Sheets import
 */
export const CHROMADB_ENDPOINTS = {
  // GET /agents/{agent_id}/chromadb/health
  HEALTH: (agentId: string) => `/agents/${agentId}/chromadb/health`,

  // POST /agents/{agent_id}/chromadb/text - Add text knowledge
  TEXT: (agentId: string) => `/agents/${agentId}/chromadb/text`,

  // POST /agents/{agent_id}/chromadb/import/excel - Import Excel file
  IMPORT_EXCEL: (agentId: string) => `/agents/${agentId}/chromadb/import/excel`,

  // POST /agents/{agent_id}/chromadb/import/google-sheets - Import Google Sheets
  IMPORT_SHEETS: (agentId: string) => `/agents/${agentId}/chromadb/import/google-sheets`,

  // POST /agents/{agent_id}/chromadb/search - Search knowledge
  SEARCH: (agentId: string) => `/agents/${agentId}/chromadb/search`,

  // GET /agents/{agent_id}/chromadb/documents - List documents
  DOCUMENTS: (agentId: string) => `/agents/${agentId}/chromadb/documents`,

  // DELETE /agents/{agent_id}/chromadb/documents/{doc_id} - Delete document
  DOCUMENT_DETAIL: (agentId: string, docId: string) =>
    `/agents/${agentId}/chromadb/documents/${docId}`,

  // DELETE /agents/{agent_id}/chromadb/ - Delete all knowledge
  DELETE_ALL: (agentId: string) => `/agents/${agentId}/chromadb/`,

  // GET /agents/{agent_id}/chromadb/stats - Get stats
  STATS: (agentId: string) => `/agents/${agentId}/chromadb/stats`,
} as const;


/**
 * Memory Endpoints (OpenMemory - For Personal Facts)
 * Alias to KNOWLEDGE_BASE_ENDPOINTS for clarity
 */
export const MEMORY_ENDPOINTS = {
  // GET /agents/{agent_id}/knowledge-base/items - List memories
  // POST /agents/{agent_id}/knowledge-base/items - Create memory
  ITEMS: (agentId: string) => `/agents/${agentId}/knowledge-base/items`,

  // GET /agents/{agent_id}/knowledge-base/items/{item_id}
  // PATCH /agents/{agent_id}/knowledge-base/items/{item_id}
  // DELETE /agents/{agent_id}/knowledge-base/items/{item_id}
  ITEM_DETAIL: (agentId: string, itemId: string) =>
    `/agents/${agentId}/knowledge-base/items/${itemId}`,

  // POST /agents/{agent_id}/knowledge-base/search
  SEARCH: (agentId: string) => `/agents/${agentId}/knowledge-base/search`,

  // GET /knowledge-base/sectors
  SECTORS: "/knowledge-base/sectors",
} as const;


/**
 * System MCP Server Endpoints (Read-only)
 * Base Path: /system/mcp-servers
 * Note: Requires Bearer Token authentication
 */
export const SYSTEM_MCP_ENDPOINTS = {
  // GET /system/mcp-servers - List all system MCP servers
  LIST: "/system/mcp-servers",

  // GET /system/mcp-servers/{server_name} - Get system MCP server detail
  DETAIL: (serverName: string) => `/system/mcp-servers/${serverName}`,

  // POST /system/mcp-servers/{server_name}/test - Test connection
  TEST: (serverName: string) => `/system/mcp-servers/${serverName}/test`,

  // POST /system/mcp-servers/reload - Reload system MCP configuration
  RELOAD: "/system/mcp-servers/reload",
} as const;

/**
 * Analytics Endpoints
 * Base Path: /analytics
 */
export const ANALYTICS_ENDPOINTS = {
  // GET /analytics/dashboard?days=7
  DASHBOARD: "/analytics/dashboard",

  // GET /analytics/usage/daily?days=30
  DAILY_USAGE: "/analytics/usage/daily",

  // GET /analytics/devices/status
  DEVICE_STATUS: "/analytics/devices/status",

  // GET /analytics/latency - Real-time AI pipeline latency
  LATENCY: "/analytics/latency",
} as const;


/**
 * Notification Endpoints
 * Base Path: /notifications
 */
export const NOTIFICATION_ENDPOINTS = {
  // POST /notifications/send/{device_id}
  SEND: (deviceId: string) => `/notifications/send/${deviceId}`,

  // POST /notifications/broadcast
  BROADCAST: "/notifications/broadcast",

  // POST /notifications/speak/{device_id}
  SPEAK: (deviceId: string) => `/notifications/speak/${deviceId}`,

  // GET /notifications/devices/connected - WebSocket connected devices
  CONNECTED_DEVICES: "/notifications/devices/connected",

  // GET /notifications/devices/mqtt - MQTT connected devices (idle but available)
  MQTT_DEVICES: "/notifications/devices/mqtt",

  // GET /notifications/devices/all - All available devices (WebSocket + MQTT)
  ALL_DEVICES: "/notifications/devices/all",
} as const;


/**
 * Marketplace Items Endpoints (Templates, Themes, Courses)
 * Base Path: /marketplace/items
 */
export const MARKETPLACE_ITEM_ENDPOINTS = {
  // GET /marketplace/items - Browse items
  BROWSE: "/marketplace/items",

  // GET /marketplace/items/{item_id} - Item detail
  DETAIL: (itemId: string) => `/marketplace/items/${itemId}`,

  // POST /marketplace/items/{item_id}/install - Install item
  INSTALL: (itemId: string) => `/marketplace/items/${itemId}/install`,

  // DELETE /marketplace/items/{item_id}/uninstall - Uninstall item
  UNINSTALL: (itemId: string) => `/marketplace/items/${itemId}/uninstall`,

  // GET /marketplace/my-installations - User installations
  MY_INSTALLATIONS: "/marketplace/my-installations",

  // POST /marketplace/items - Create item
  CREATE: "/marketplace/items",

  // PUT /marketplace/items/{item_id}/submit - Submit for review
  SUBMIT: (itemId: string) => `/marketplace/items/${itemId}/submit`,

  // PUT /marketplace/items/{item_id}/approve - Approve item (admin)
  APPROVE: (itemId: string) => `/marketplace/items/${itemId}/approve`,

  // POST /marketplace/items/{item_id}/reviews - Add review
  ADD_REVIEW: (itemId: string) => `/marketplace/items/${itemId}/reviews`,

  // GET /marketplace/items/{item_id}/reviews - Get reviews
  REVIEWS: (itemId: string) => `/marketplace/items/${itemId}/reviews`,
} as const;

/**
 * Helper function to get all endpoints
 */
export const API_ENDPOINTS = {
  AUTH: AUTH_ENDPOINTS,
  USER: USER_ENDPOINTS,
  CHAT: CHAT_ENDPOINTS,
  MESSAGE: MESSAGE_ENDPOINTS,
  DEVICE: DEVICE_ENDPOINTS,
  AGENT: AGENT_ENDPOINTS,
  TEMPLATE: TEMPLATE_ENDPOINTS,
  PROVIDER: PROVIDER_ENDPOINTS,
  TOOL: TOOL_ENDPOINTS,
  KNOWLEDGE_BASE: KNOWLEDGE_BASE_ENDPOINTS,
  MCP: MCP_ENDPOINTS,
  AGENT_MCP: AGENT_MCP_ENDPOINTS,
  AGENT_TOOL: AGENT_TOOL_ENDPOINTS, // @deprecated Use AGENT_MCP
  PLUGIN: PLUGIN_ENDPOINTS,
  SYSTEM_MCP: SYSTEM_MCP_ENDPOINTS,
  ANALYTICS: ANALYTICS_ENDPOINTS,
  NOTIFICATIONS: NOTIFICATION_ENDPOINTS,
  MARKETPLACE_ITEM: MARKETPLACE_ITEM_ENDPOINTS,
} as const;

export default API_ENDPOINTS;
