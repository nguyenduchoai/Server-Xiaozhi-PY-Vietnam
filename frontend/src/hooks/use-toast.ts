/**
 * Simple toast hook using native browser alerts
 * TODO: Replace with proper toast library (e.g., sonner, react-hot-toast)
 */

import { useCallback } from "react";

interface ToastOptions {
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
}

export function useToast() {
  const toast = useCallback((options: ToastOptions) => {
    const message = options.description || options.title || "Notification";
    if (options.variant === "destructive") {
      console.error("[Toast Error]:", message);
    } else {
      // Toast notification shown
    }
    // Use native alert for now - in production, replace with proper toast
    // alert(message);
  }, []);

  return { toast };
}
