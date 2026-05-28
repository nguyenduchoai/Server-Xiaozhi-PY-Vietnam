/**
 * Application Logger Utility
 * 
 * Provides environment-aware logging that can be disabled in production.
 * Wraps console methods to allow centralized control over logging behavior.
 * 
 * Usage:
 *   import { logger } from '@/utils/logger';
 *   logger.debug('[Module]', 'Debug message');
 *   logger.info('[Module]', 'Info message');
 *   logger.warn('[Module]', 'Warning message');
 *   logger.error('[Module]', 'Error message', error);
 */

// Check if we're in development mode
const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development';

// Log levels that can be enabled/disabled
const LOG_LEVELS = {
    debug: isDevelopment,   // Only in development
    info: isDevelopment,    // Only in development
    warn: true,             // Always enabled
    error: true,            // Always enabled
} as const;

/**
 * Logger interface with environment-aware methods
 */
export const logger = {
    /**
     * Debug level - only logs in development
     */
    debug: (...args: unknown[]): void => {
        if (LOG_LEVELS.debug) {
            console.log(...args);
        }
    },

    /**
     * Info level - only logs in development
     */
    info: (...args: unknown[]): void => {
        if (LOG_LEVELS.info) {
            console.log(...args);
        }
    },

    /**
     * Warning level - always logs
     */
    warn: (...args: unknown[]): void => {
        if (LOG_LEVELS.warn) {
            console.warn(...args);
        }
    },

    /**
     * Error level - always logs
     */
    error: (...args: unknown[]): void => {
        if (LOG_LEVELS.error) {
            console.error(...args);
        }
    },

    /**
     * Group logs together (development only)
     */
    group: (label: string): void => {
        if (isDevelopment) {
            console.group(label);
        }
    },

    /**
     * End group (development only)
     */
    groupEnd: (): void => {
        if (isDevelopment) {
            console.groupEnd();
        }
    },

    /**
     * Table display (development only)
     */
    table: (data: unknown): void => {
        if (isDevelopment) {
            console.table(data);
        }
    },
};

export default logger;
