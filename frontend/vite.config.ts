/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@components": path.resolve(__dirname, "./src/components"),
      "@hooks": path.resolve(__dirname, "./src/hooks"),
      "@queries": path.resolve(__dirname, "./src/queries"),
      "@types": path.resolve(__dirname, "./src/types"),
      "@store": path.resolve(__dirname, "./src/store"),
      "@config": path.resolve(__dirname, "./src/config"),
      "@lib": path.resolve(__dirname, "./src/lib"),
      "@layouts": path.resolve(__dirname, "./src/layouts"),
      "@pages": path.resolve(__dirname, "./src/pages"),
      "@api": path.resolve(__dirname, "./src/lib/api"),
      "@utils": path.resolve(__dirname, "./src/lib/utils.ts"),
      "@locales": path.resolve(__dirname, "./src/locales"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  // ============================================================================
  // VITEST CONFIG — Enterprise Testing Infrastructure
  // ============================================================================
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
    // Coverage configuration
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/test/**",
        "src/main.tsx",
        "src/vite-env.d.ts",
      ],
      thresholds: {
        // Minimum coverage thresholds for CI gates
        statements: 30,
        branches: 25,
        functions: 25,
        lines: 30,
      },
    },
    // Reporter config
    reporters: ["default"],
    // Include patterns
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
  build: {
    // Increase chunk size warning limit (optional, helps reduce noise)
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Manual chunks for code splitting - reduces main bundle size
        manualChunks: {
          // React core libraries
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          // UI framework chunks
          "vendor-ui": [
            "@radix-ui/react-dialog",
            "@radix-ui/react-dropdown-menu",
            "@radix-ui/react-select",
            "@radix-ui/react-tabs",
            "@radix-ui/react-tooltip",
            "@radix-ui/react-popover",
            "@radix-ui/react-switch",
            "@radix-ui/react-alert-dialog",
            "@radix-ui/react-checkbox",
            "@radix-ui/react-scroll-area",
          ],
          // Data/state management
          "vendor-data": [
            "@tanstack/react-query",
            "zustand",
            "axios",
          ],
          // Form handling
          "vendor-forms": [
            "react-hook-form",
            "@hookform/resolvers",
            "zod",
          ],
          // Icons and utilities
          "vendor-icons": ["lucide-react"],
          // i18n
          "vendor-i18n": ["i18next", "react-i18next"],
        },
      },
    },
  },
});
