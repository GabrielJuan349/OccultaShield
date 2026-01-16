/**
 * Admin Initialization Script
 * Creates default admin user on Better Auth startup if it doesn't exist
 */
import { getAuth } from './auth';
import { logger } from './logger';

/**
 * Creates or updates the admin user using Better-Auth
 * Uses environment variables: ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NAME
 */
export async function initializeAdminUser() {
    // Check if admin credentials are configured
    const adminEmail = process.env['ADMIN_EMAIL'];
    const adminPassword = process.env['ADMIN_PASSWORD'];
    const adminName = process.env['ADMIN_NAME'] || 'Admin';

    if (!adminEmail || !adminPassword) {
        logger.warn('⚠️  No admin credentials configured (ADMIN_EMAIL, ADMIN_PASSWORD)', {
            adminEmail: adminEmail ? 'set' : 'missing',
            adminPassword: adminPassword ? 'set' : 'missing',
        });
        return;
    }

    logger.info(`🔧 Initializing admin user via Better-Auth...`, { email: adminEmail, name: adminName });

    try {
        const auth = await getAuth();

        // Try to sign up the admin user
        // If the user already exists, Better-Auth will throw an exception
        logger.debug(`📝 Attempting to create admin user...`);

        let userAlreadyExists = false;

        try {
            const result = await auth.api.signUpEmail({
                body: {
                    email: adminEmail,
                    password: adminPassword,
                    name: adminName,
                },
            });

            // User created successfully
            logger.info(`✅ Admin user created successfully: ${adminEmail}`);

            // Now update the role to admin (Better-Auth creates users with role 'user' by default)
            const { getDb } = await import('./db');
            const db = await getDb();

            await db.query(
                `UPDATE user SET role = 'admin', isApproved = true, emailVerified = true WHERE email = $email`,
                { email: adminEmail }
            );

            logger.info(`✅ Admin role and permissions set`);
        } catch (signupError: any) {
            // Check if the error is because user already exists
            const errorMsg = signupError?.message || signupError?.body?.message || String(signupError);
            const errorCode = signupError?.body?.code;

            if (errorMsg.toLowerCase().includes('exist') ||
                errorMsg.toLowerCase().includes('duplicate') ||
                errorMsg.toLowerCase().includes('unique') ||
                errorCode === 'USER_ALREADY_EXISTS_USE_ANOTHER_EMAIL') {
                // User already exists - this is OK
                userAlreadyExists = true;
            } else {
                // Different error - re-throw to outer catch
                throw signupError;
            }
        }

        // Handle existing user case
        if (userAlreadyExists) {
            logger.info(`✅ Admin user already exists: ${adminEmail}`);
            logger.debug(`🔧 Ensuring admin has correct role...`);

            const { getDb } = await import('./db');
            const db = await getDb();

            await db.query(
                `UPDATE user SET role = 'admin', isApproved = true, emailVerified = true WHERE email = $email`,
                { email: adminEmail }
            );

            logger.info(`✅ Admin role and permissions updated`);
        }

        logger.info(`🎉 Admin initialization complete!`, {
            email: adminEmail,
            role: 'admin',
            approved: true,
            emailVerified: true,
        });

    } catch (error) {
        logger.error('❌ Failed to initialize admin user', { error: (error as Error).message });
        // Don't throw - allow server to start even if admin creation fails
    }
}
