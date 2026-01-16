/**
 * Admin API Routes for OccultaShield.
 *
 * Provides Express routes for the admin dashboard including:
 * - User management (list, approve, reject, role updates)
 * - Dashboard statistics (users, videos, violations)
 * - Application settings (closed beta mode)
 * - Audit log access
 *
 * All routes require admin role authentication via the requireAdmin middleware.
 *
 * @example
 * Routes:
 * - GET /admin/stats - Dashboard statistics
 * - GET /admin/users - List all users
 * - PATCH /admin/users/:id/approve - Approve a user
 * - GET /admin/audit-log - View audit entries
 */
import { Router, Request, Response, NextFunction } from 'express';
import { getDb, parseRecordId, createRecordId } from './db';
import { getAuth } from './auth';
import { sendApprovalEmail, sendRejectionEmail } from './email';
import { logger } from './logger';

export const adminRouter = Router();

// =============================================================================
// MIDDLEWARE: Require Admin Role
// =============================================================================

interface AuthRequest extends Request {
    user?: {
        id: string;
        email: string;
        name: string;
        role: string;
    };
}

async function requireAdmin(req: AuthRequest, res: Response, next: NextFunction): Promise<void> {
    try {
        const auth = await getAuth();

        // DEBUG: Log raw incoming headers for diagnosis
        logger.debug('🔍 [requireAdmin] Incoming request headers', {
            authorization: req.headers['authorization'] ? 'PRESENT' : 'NOT PRESENT',
            cookie: req.headers['cookie'] ? 'PRESENT' : 'NOT PRESENT',
            origin: req.headers['origin'],
            host: req.headers['host'],
        });

        // Mejoramos la extracción de headers para Better-Auth
        const headers = new Headers();
        for (const [key, value] of Object.entries(req.headers)) {
            if (value) {
                // Asegurar que las cookies y authorization se pasen íntegras
                headers.set(key, Array.isArray(value) ? value.join(', ') : value);
            }
        }

        // DEBUG: Log constructed Headers object
        logger.debug('🔍 [requireAdmin] Headers passed to getSession', {
            authorization: headers.get('authorization') ? 'PRESENT' : 'NOT PRESENT',
            cookie: headers.get('cookie') ? 'PRESENT' : 'NOT PRESENT',
        });

        // Better-Auth getSession puede recibir el objeto headers directamente
        const session = await auth.api.getSession({
            headers: headers
        });

        logger.debug('📋 Session check result', {
            hasSession: !!session,
            hasUser: !!session?.user,
            userEmail: session?.user?.email,
            userRole: session?.user?.role,
        });

        if (!session?.user) {
            logger.warn('⚠️ Admin Access Denied: No session found');
            // Log all cookie names for diagnosis
            const cookieHeader = req.headers.cookie || '';
            const cookieNames = cookieHeader.split(';').map(c => c.trim().split('=')[0]).filter(Boolean);
            logger.debug('🍪 Cookie names received', { cookies: cookieNames });
            logger.debug('💡 Tip: If cookies are empty but Authorization is present, check if Better-Auth is configured to accept Bearer tokens.');
            res.status(401).json({ error: 'Not authenticated' });
            return;
        }

        if (session.user.role !== 'admin') {
            logger.warn(`⚠️ Admin Access Denied: User ${session.user.email} is not an admin`);
            res.status(403).json({ error: 'Admin access required' });
            return;
        }

        req.user = session.user as AuthRequest['user'];
        next();
    } catch (error) {
        logger.error('❌ Admin auth error', { error: (error as Error).message });
        res.status(401).json({ error: 'Authentication failed' });
    }
}

// =============================================================================
// ENDPOINTS: Statistics
// =============================================================================

adminRouter.get('/stats', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const db = await getDb();

        // Count users
        const usersResult = await db.query<[{ count: number; isApproved: boolean }[]]>(
            'SELECT count() as count, isApproved FROM user GROUP BY isApproved'
        );

        let totalUsers = 0, pendingUsers = 0, approvedUsers = 0;
        if (usersResult[0]) {
            for (const row of usersResult[0]) {
                if (row.isApproved) approvedUsers = row.count;
                else pendingUsers = row.count;
                totalUsers += row.count;
            }
        }

        // Count videos
        const videosResult = await db.query<[{ count: number }[]]>('SELECT count() as count FROM video');
        const totalVideos = videosResult[0]?.[0]?.count ?? 0;

        // Count violations
        const violationsResult = await db.query<[{ count: number }[]]>(
            'SELECT count() as count FROM gdpr_verification WHERE is_violation = true'
        );
        const totalViolations = violationsResult[0]?.[0]?.count ?? 0;

        // Count active sessions
        const sessionsResult = await db.query<[{ count: number }[]]>(
            'SELECT count() as count FROM session WHERE expiresAt > time::now()'
        );
        const activeSessions = sessionsResult[0]?.[0]?.count ?? 0;

        // Recent activity (last 10 audit log entries)
        const activityResult = await db.query<[Record<string, unknown>[]]>(
            'SELECT * FROM audit_log ORDER BY createdAt DESC LIMIT 10'
        );
        const recentActivity = (activityResult[0] || []).map(a => ({
            id: parseRecordId(a['id']),
            action: a['action'] || '',
            targetId: a['targetId'] || '',
            status: 'success',
            createdAt: a['createdAt'] || ''
        }));

        res.json({
            total_users: totalUsers,
            pending_users: pendingUsers,
            approved_users: approvedUsers,
            total_videos: totalVideos,
            total_violations: totalViolations,
            active_sessions: activeSessions,
            recentActivity
        });
    } catch (error) {
        logger.error('❌ Error fetching stats', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to fetch stats' });
    }
});

// =============================================================================
// ENDPOINTS: User Management
// =============================================================================

adminRouter.get('/users', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const db = await getDb();
        const result = await db.query<[Record<string, unknown>[]]>(
            'SELECT * FROM user ORDER BY createdAt DESC'
        );

        const users = (result[0] || []).map(u => ({
            id: parseRecordId(u['id']),
            name: u['name'] || '',
            email: u['email'] || '',
            role: u['role'] || 'user',
            isApproved: u['isApproved'] ?? false,
            usageType: u['usageType'] || 'individual',
            createdAt: u['createdAt'] || '',
            image: u['image']
        }));

        res.json(users);
    } catch (error) {
        logger.error('❌ Error fetching users', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to fetch users' });
    }
});

adminRouter.get('/users/pending', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const db = await getDb();
        const result = await db.query<[Record<string, unknown>[]]>(
            'SELECT * FROM user WHERE isApproved = false ORDER BY createdAt DESC'
        );

        const users = (result[0] || []).map(u => ({
            id: parseRecordId(u['id']),
            name: u['name'] || '',
            email: u['email'] || '',
            usageType: u['usageType'] || 'individual',
            createdAt: u['createdAt'] || ''
        }));

        res.json(users);
    } catch (error) {
        logger.error('❌ Error fetching pending users', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to fetch pending users' });
    }
});

adminRouter.patch('/users/:userId/approve', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const userId = req.params['userId'] as string;
        const db = await getDb();
        // Extract clean ID without 'user:' prefix if present
        const cleanUserId = userId.includes(':') ? userId.split(':')[1] : userId;

        // Get user info before updating
        const userResult = await db.query<[Record<string, unknown>[]]>(
            'SELECT email, name FROM user WHERE id = type::thing("user", $userId)',
            { userId: cleanUserId }
        );
        const user = userResult[0]?.[0];

        // Update user
        await db.query('UPDATE type::thing("user", $userId) SET isApproved = true, updatedAt = time::now()', { userId: cleanUserId });

        // Log action
        const adminUserId = req.user!.id.includes(':') ? req.user!.id.split(':')[1] : req.user!.id;
        await db.query(
            `CREATE audit_log SET userId = type::thing('user', $adminUserId), action = 'user_approved', targetId = $targetId, metadata = { approved_by: $adminName }`,
            { adminUserId, targetId: userId, adminName: req.user!.name }
        );

        // Send email notification
        if (user) {
            await sendApprovalEmail(user['email'] as string, user['name'] as string);
        }

        res.json({ status: 'approved', user_id: userId });
    } catch (error) {
        logger.error('❌ Error approving user', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to approve user' });
    }
});

adminRouter.patch('/users/:userId/reject', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const userId = req.params['userId'] as string;
        const db = await getDb();
        // Extract clean ID without 'user:' prefix if present
        const cleanUserId = userId.includes(':') ? userId.split(':')[1] : userId;

        // Get user info before deleting
        const userResult = await db.query<[Record<string, unknown>[]]>(
            'SELECT email, name FROM user WHERE id = type::thing("user", $userId)',
            { userId: cleanUserId }
        );
        const user = userResult[0]?.[0];

        // Log action before deletion
        const adminUserId = req.user!.id.includes(':') ? req.user!.id.split(':')[1] : req.user!.id;
        await db.query(
            `CREATE audit_log SET userId = type::thing('user', $adminUserId), action = 'user_rejected', targetId = $targetId, metadata = { rejected_by: $adminName }`,
            { adminUserId, targetId: userId, adminName: req.user!.name }
        );

        // Delete related records
        await db.query('DELETE session WHERE userId = type::thing("user", $userId)', { userId: cleanUserId });
        await db.query('DELETE account WHERE userId = type::thing("user", $userId)', { userId: cleanUserId });
        await db.query('DELETE type::thing("user", $userId)', { userId: cleanUserId });

        // Send rejection email
        if (user) {
            await sendRejectionEmail(user['email'] as string, user['name'] as string);
        }

        res.json({ status: 'rejected', user_id: userId });
    } catch (error) {
        logger.error('❌ Error rejecting user', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to reject user' });
    }
});

adminRouter.patch('/users/:userId/role', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const userId = req.params['userId'] as string;
        const { role } = req.body;
        const db = await getDb();
        // Extract clean ID without 'user:' prefix if present
        const cleanUserId = userId.includes(':') ? userId.split(':')[1] : userId;

        await db.query('UPDATE type::thing("user", $userId) SET role = $role, updatedAt = time::now()', { userId: cleanUserId, role });

        // Log action
        const adminUserId = req.user!.id.includes(':') ? req.user!.id.split(':')[1] : req.user!.id;
        await db.query(
            `CREATE audit_log SET userId = type::thing('user', $adminUserId), action = 'role_changed', targetId = $targetId, metadata = { new_role: $newRole, changed_by: $adminName }`,
            { adminUserId, targetId: userId, newRole: role, adminName: req.user!.name }
        );

        res.json({ status: 'updated', user_id: userId, role });
    } catch (error) {
        logger.error('❌ Error updating role', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to update role' });
    }
});

// =============================================================================
// ENDPOINTS: Settings
// =============================================================================

adminRouter.get('/settings', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const db = await getDb();
        const result = await db.query<[Record<string, unknown>[]]>('SELECT * FROM app_settings');

        const settings: Record<string, unknown> = { closedBetaMode: true };
        if (result[0]) {
            for (const s of result[0]) {
                settings[s['key'] as string] = s['value'];
            }
        }

        res.json(settings);
    } catch (error) {
        logger.error('❌ Error fetching settings', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to fetch settings' });
    }
});

adminRouter.put('/settings/:key', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const { key } = req.params;
        const { value } = req.body;
        const db = await getDb();

        // Upsert setting
        await db.query(
            `UPSERT app_settings SET key = $key, value = $value, updatedAt = time::now() WHERE key = $key`,
            { key, value }
        );

        // Log action
        const adminUserId = req.user!.id.includes(':') ? req.user!.id.split(':')[1] : req.user!.id;
        await db.query(
            `CREATE audit_log SET userId = type::thing('user', $adminUserId), action = 'settings_changed', targetId = $key, metadata = { new_value: $value, changed_by: $adminName }`,
            { adminUserId, key, value: String(value), adminName: req.user!.name }
        );

        res.json({ status: 'updated', key, value });
    } catch (error) {
        logger.error('❌ Error updating setting', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to update setting' });
    }
});

// =============================================================================
// ENDPOINTS: Audit Log
// =============================================================================

adminRouter.get('/audit-log', requireAdmin, async (req: AuthRequest, res: Response) => {
    try {
        const db = await getDb();
        const limit = Number(req.query['limit']) || 50;
        const action = req.query['action'] as string | undefined;

        let query = 'SELECT * FROM audit_log ORDER BY createdAt DESC LIMIT $limit';
        const params: Record<string, unknown> = { limit };

        if (action) {
            query = 'SELECT * FROM audit_log WHERE action = $action ORDER BY createdAt DESC LIMIT $limit';
            params['action'] = action;
        }

        const result = await db.query<[Record<string, unknown>[]]>(query, params);
        res.json(result[0] || []);
    } catch (error) {
        logger.error('❌ Error fetching audit log', { error: (error as Error).message });
        res.status(500).json({ error: 'Failed to fetch audit log' });
    }
});

// =============================================================================
// MIDDLEWARE: Check User Approval (for protected routes)
// =============================================================================

export async function checkUserApproval(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
        const auth = await getAuth();
        // Convert IncomingHttpHeaders to Record<string, string>
        const headers: Record<string, string> = {};
        for (const [key, value] of Object.entries(req.headers)) {
            if (value) headers[key] = Array.isArray(value) ? value[0] : value;
        }
        const session = await auth.api.getSession({ headers });

        if (!session?.user) {
            next(); // Not authenticated, let other middleware handle it
            return;
        }

        // Admins bypass approval check
        if (session.user.role === 'admin') {
            next();
            return;
        }

        // Check if closed beta mode is enabled
        const db = await getDb();
        const settingsResult = await db.query<[{ value: unknown }[]]>(
            `SELECT value FROM app_settings WHERE key = 'closedBetaMode'`
        );
        const closedBeta = settingsResult[0]?.[0]?.value ?? true;

        if (closedBeta) {
            // Check user approval status
            const userId = createRecordId('user', session.user.id);
            const userResult = await db.query<[{ isApproved: boolean }[]]>(
                'SELECT isApproved FROM user WHERE id = $id',
                { id: userId }
            );

            const isApproved = userResult[0]?.[0]?.isApproved ?? false;

            if (!isApproved) {
                res.status(403).json({
                    error: 'pending_approval',
                    message: 'Tu cuenta está pendiente de aprobación. Un administrador revisará tu solicitud en 1-2 días.'
                });
                return;
            }
        }

        next();
    } catch (error) {
        logger.error('❌ Approval check error', { error: (error as Error).message });
        next(); // Continue on error to not block legitimate requests
    }
}
