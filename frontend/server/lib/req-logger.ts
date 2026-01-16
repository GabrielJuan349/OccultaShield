/**
 * Request Logging Middleware for OccultaShield SSR Server.
 *
 * Provides Express middleware for automatic request/response logging
 * with timing, request IDs, and structured metadata.
 *
 * Features:
 * - Automatic X-Request-ID generation/extraction
 * - Request duration measurement
 * - Status code based emoji indicators
 * - Configurable path exclusions
 *
 * @example
 * ```typescript
 * import { requestLogger } from '#server/req-logger';
 * app.use(requestLogger);
 * ```
 */

import { Request, Response, NextFunction } from 'express';
import { randomUUID } from 'node:crypto';
import { logger } from './logger';

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Paths to exclude from request logging (health checks, etc.)
 */
const EXCLUDED_PATHS = new Set([
    '/health',
    '/healthz',
    '/ready',
    '/favicon.ico',
]);

/**
 * Path prefixes to log at DEBUG level instead of INFO.
 */
const DEBUG_PATH_PREFIXES = [
    '/browser/',  // Static assets
    '/assets/',   // Static assets
];

// =============================================================================
// MIDDLEWARE
// =============================================================================

/**
 * Express middleware for request/response logging.
 *
 * Logs incoming requests and outgoing responses with:
 * - HTTP method and path
 * - Response status code
 * - Request duration in milliseconds
 * - Request ID for tracing
 *
 * @example
 * ```typescript
 * app.use(requestLogger);
 * // Logs: "GET /api/auth/session" and "200 GET /api/auth/session (45ms)"
 * ```
 */
export function requestLogger(req: Request, res: Response, next: NextFunction): void {
    // Skip excluded paths
    if (EXCLUDED_PATHS.has(req.path)) {
        next();
        return;
    }

    // Check if this is a debug-level path (static assets)
    const isDebugPath = DEBUG_PATH_PREFIXES.some(prefix => req.path.startsWith(prefix));

    // Get or generate request ID
    let requestId = req.headers['x-request-id'] as string | undefined;
    if (!requestId) {
        requestId = randomUUID();
    }

    // Add request ID to response headers
    res.setHeader('X-Request-ID', requestId);

    // Store request ID on request object for downstream use
    (req as Request & { requestId?: string }).requestId = requestId;

    // Start timing
    const startTime = process.hrtime.bigint();

    // Log request start (skip for debug paths)
    if (!isDebugPath) {
        logger.info(`${req.method} ${req.path}`, {
            requestId: requestId.slice(0, 8),
            method: req.method,
            path: req.path,
            query: Object.keys(req.query).length > 0 ? req.query : undefined,
            ip: getClientIp(req),
        });
    }

    // Hook into response finish event
    res.on('finish', () => {
        const duration = Number(process.hrtime.bigint() - startTime) / 1e6; // Convert to ms
        const statusEmoji = getStatusEmoji(res.statusCode);

        const logData = {
            requestId: requestId!.slice(0, 8),
            status: res.statusCode,
            duration: `${duration.toFixed(1)}ms`,
            method: req.method,
            path: req.path,
        };

        // Choose log level based on status and path
        if (res.statusCode >= 500) {
            logger.error(`${statusEmoji} ${res.statusCode} ${req.method} ${req.path} (${duration.toFixed(1)}ms)`, logData);
        } else if (res.statusCode >= 400) {
            logger.warn(`${statusEmoji} ${res.statusCode} ${req.method} ${req.path} (${duration.toFixed(1)}ms)`, logData);
        } else if (isDebugPath) {
            logger.debug(`${statusEmoji} ${res.statusCode} ${req.method} ${req.path} (${duration.toFixed(1)}ms)`, logData);
        } else {
            logger.info(`${statusEmoji} ${res.statusCode} ${req.method} ${req.path} (${duration.toFixed(1)}ms)`, logData);
        }
    });

    next();
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get emoji indicator based on HTTP status code.
 */
function getStatusEmoji(statusCode: number): string {
    if (statusCode < 300) return '\u2713';  // Checkmark
    if (statusCode < 400) return '\u21AA';  // Arrow
    if (statusCode < 500) return '\u26A0';  // Warning
    return '\u2717';  // X mark
}

/**
 * Extract client IP from request, handling proxies.
 */
function getClientIp(req: Request): string {
    const forwarded = req.headers['x-forwarded-for'];
    if (forwarded) {
        return Array.isArray(forwarded) ? forwarded[0] : forwarded.split(',')[0].trim();
    }

    const realIp = req.headers['x-real-ip'];
    if (realIp) {
        return Array.isArray(realIp) ? realIp[0] : realIp;
    }

    return req.socket.remoteAddress || 'unknown';
}

export default requestLogger;
