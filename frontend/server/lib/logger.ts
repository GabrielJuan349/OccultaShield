/**
 * Unified Logger for OccultaShield SSR Server.
 *
 * Provides Winston-based logging with environment-aware formatting:
 * - Development: Colored console output with timestamps
 * - Production: JSON structured logs for aggregation
 *
 * Features:
 * - Log levels: error, warn, info, debug
 * - Request ID context support
 * - Colored output for terminal readability
 * - JSON format for log aggregation systems
 *
 * @example
 * ```typescript
 * import { logger } from '#server/logger';
 * logger.info('Server started', { port: 4201 });
 * logger.error('Connection failed', { error: err.message });
 * ```
 */

import winston from 'winston';
import { ENV } from './env';

// =============================================================================
// CONFIGURATION
// =============================================================================

const isProduction = ENV.NODE_ENV === 'production';
const logLevel = process.env['LOG_LEVEL'] || (isProduction ? 'info' : 'debug');

// =============================================================================
// FORMATTERS
// =============================================================================

/**
 * Custom colored format for development console output.
 */
const coloredFormat = winston.format.combine(
    winston.format.timestamp({ format: 'HH:mm:ss.SSS' }),
    winston.format.colorize({ all: false }),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
        // Color codes for levels
        const levelColors: Record<string, string> = {
            error: '\x1b[31m',   // Red
            warn: '\x1b[33m',    // Yellow
            info: '\x1b[32m',    // Green
            debug: '\x1b[36m',   // Cyan
        };
        const reset = '\x1b[0m';
        const dim = '\x1b[2m';
        const bold = '\x1b[1m';

        const levelName = level.replace(/\x1b\[\d+m/g, '').toUpperCase();
        const color = levelColors[level.replace(/\x1b\[\d+m/g, '')] || '';

        // Format metadata if present
        let metaStr = '';
        if (Object.keys(meta).length > 0) {
            // Filter out internal Winston properties
            const cleanMeta = Object.fromEntries(
                Object.entries(meta).filter(([k]) => !['splat', 'level', 'timestamp'].includes(k))
            );
            if (Object.keys(cleanMeta).length > 0) {
                metaStr = ` ${dim}${JSON.stringify(cleanMeta)}${reset}`;
            }
        }

        return `${dim}${timestamp}${reset} ${color}${bold}${levelName.padEnd(5)}${reset} ${message}${metaStr}`;
    })
);

/**
 * JSON format for production environments.
 */
const jsonFormat = winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DDTHH:mm:ss.SSSZ' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
);

// =============================================================================
// LOGGER INSTANCE
// =============================================================================

/**
 * Winston logger instance configured for OccultaShield SSR server.
 *
 * @example
 * ```typescript
 * logger.info('Request received', { method: 'GET', path: '/api/auth' });
 * logger.error('Database connection failed', { error: err.message });
 * logger.debug('Session validated', { userId: user.id });
 * ```
 */
export const logger = winston.createLogger({
    level: logLevel,
    format: isProduction ? jsonFormat : coloredFormat,
    defaultMeta: { service: 'occultashield-ssr' },
    transports: [
        new winston.transports.Console({
            stderrLevels: ['error'],
        }),
    ],
});

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Create a child logger with additional context.
 *
 * @param context - Additional metadata to include in all log messages
 * @returns Child logger instance
 *
 * @example
 * ```typescript
 * const reqLogger = createChildLogger({ requestId: 'abc123' });
 * reqLogger.info('Processing request');
 * ```
 */
export function createChildLogger(context: Record<string, unknown>): winston.Logger {
    return logger.child(context);
}

/**
 * Log a startup message with service information.
 */
export function logStartup(port: number): void {
    logger.info(`🚀 OccultaShield SSR Server starting on port ${port}`, {
        port,
        environment: ENV.NODE_ENV,
        logLevel,
    });
}

/**
 * Log a successful initialization message.
 */
export function logReady(port: number): void {
    logger.info(`✅ OccultaShield Server running at http://localhost:${port}`);
    logger.info(`   Auth endpoints: http://localhost:${port}/api/auth/*`);
    logger.info(`   Angular SSR: Enabled`);
}

export default logger;
