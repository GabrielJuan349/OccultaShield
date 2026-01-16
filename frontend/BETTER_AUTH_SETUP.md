# OccultaShield - Better-Auth Setup Guide

## Tech Stack

- **Runtime**: Bun / Node.js
- **Framework**: Angular v21 with SSR
- **Database**: SurrealDB
- **Authentication**: Better-Auth
- **Email**: Nodemailer (Gmail SMTP)

## File Structure

```
├── server/
│   ├── lib/
│   │   ├── admin.ts       # Admin API routes (users, settings, audit)
│   │   ├── auth.ts        # Better-Auth configuration + SurrealDB Adapter
│   │   ├── db.ts          # SurrealDB connection and helpers
│   │   ├── email.ts       # Email service (Nodemailer templates)
│   │   ├── env.ts         # Environment variables configuration
│   │   └── init-admin.ts  # Initial admin user creation script
│   └── tsconfig.json      # TypeScript config for server
├── src/
│   ├── app/
│   │   ├── lib/
│   │   │   └── auth-client.ts     # Better-Auth client for Angular
│   │   └── services/
│   │       ├── admin.service.ts   # Angular admin service (HTTP + signals)
│   │       └── auth.service.ts    # Angular authentication service
│   └── server.ts          # Express server with SSR + Better-Auth handler
└── .env.example           # Example environment variables
```

## Initial Setup

### 1. Install Dependencies

```bash
bun install
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

**Important variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `SURREALDB_HOST` | SurrealDB host | `127.0.0.1` |
| `SURREALDB_PORT` | SurrealDB port | `8000` |
| `SURREALDB_NAMESPACE` | DB Namespace | `occultashield` |
| `SURREALDB_DB` | DB Name | `main` |
| `SURREALDB_USER` | DB User | `root` |
| `SURREALDB_PASS` | DB Password | `root` |
| `BETTERAUTH_SECRET` | **IMPORTANT** - Auth secret (32+ chars) | |
| `SMTP_USER` | Gmail address for notifications | |
| `SMTP_PASS` | Google App Password | |
| `SMTP_FROM` | Sender address (optional) | |
| `ADMIN_EMAIL` | Initial admin email (auto-created) | |
| `ADMIN_PASSWORD` | Initial admin password | |
| `ADMIN_NAME` | Initial admin name | `Admin` |

### 3. Start SurrealDB

```bash
# Start SurrealDB in development mode
surreal start --user root --pass root memory
```

### 4. Import Database Schema

```bash
# The schema includes user, session, app_settings, audit_log, and processing_log tables
surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns occultashield --db main \
  db_files/schema.surql
```

### 5. Configure the First Administrator

**Option A: Automatic (recommended)** - Set environment variables:
```env
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your-secure-password
ADMIN_NAME=Administrator
```
The server will automatically create the admin user on startup via `init-admin.ts`.

**Option B: Manual** - Run this SQL command:
```sql
UPDATE user:id SET role = 'admin', isApproved = true, emailVerified = true;
```

---

## 🛡️ Admin API & SSR

The administration logic runs on the **Node.js Express SSR server** for enhanced security and direct access to SurrealDB.

### Administration Endpoints (`/api/admin/*`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/stats` | GET | Dashboard statistics (users, videos, sessions) |
| `/api/admin/users` | GET | List of all users |
| `/api/admin/users/pending` | GET | List of pending approval users |
| `/api/admin/users/:id/approve` | PATCH | Approve user + Send approval email |
| `/api/admin/users/:id/reject` | PATCH | Reject user + Delete + Send rejection email |
| `/api/admin/users/:id/role` | PATCH | Update user role (`user` / `admin`) |
| `/api/admin/settings` | GET | Get app settings |
| `/api/admin/settings/closedBetaMode` | PUT | Toggle closed beta mode |
| `/api/admin/audit-log` | GET | Get audit log (with optional filters) |

### Other API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/*` | ALL | Better-Auth authentication routes |
| `/api/upload/log` | POST | Log upload activity to `processing_log` |

---

## 🚪 Approval Flow (Closed Beta)

1.  **Registration**: Upon registration, the user automatically receives a "Request Received" email via `sendPendingNotification()`. Initial state: `isApproved: false`.
2.  **Middlewares**: 
    *   `requireAdmin`: Protects `/api/admin/*` routes by checking session and role.
    *   `checkUserApproval`: Blocks app routes if user is not approved and `closedBetaMode` is active.
3.  **Email Templates**: Professional HTML emails sent via **Nodemailer**:
    *   `sendPendingNotification()` - When user registers
    *   `sendApprovalEmail()` - When admin approves
    *   `sendRejectionEmail()` - When admin rejects

---

## Database Schema (Extended)

Main authentication and control tables:

| Table | Description |
|-------|-------------|
| **user** | User accounts with `role`, `isApproved`, `usageType`, `emailVerified` |
| **session** | Active sessions with expiration |
| **account** | OAuth/credential accounts linked to users |
| **verification** | Email verification tokens |
| **app_settings** | System configuration (e.g., `closedBetaMode`) |
| **audit_log** | Historical log of administrative actions |
| **processing_log** | Video upload/processing activity log |

---

## Available Signals in AuthService

| Signal | Type | Description |
|--------|------|-------------|
| `user` | `User \| null` | Authenticated user object |
| `session` | `Session \| null` | Current session data |
| `isAuthenticated` | `boolean` | Whether there is an active session |
| `isLoading` | `boolean` | Authentication operation in progress |
| `error` | `string \| null` | Last error message |
| `userRole` | `string` | Current role (`user` or `admin`) |
| `isApproved` | `boolean` | User's approval status |

### AuthService Methods

| Method | Description |
|--------|-------------|
| `checkSession()` | Verify and refresh session |
| `login(email, password)` | Sign in with credentials |
| `register(email, password, name, usageType)` | Create new account |
| `logout()` | Sign out and clear session |
| `getToken()` | Get session token for API calls |
| `hasRole(role)` | Check if user has specific role |
| `isAdmin()` | Check if user is administrator |
| `refreshUserFromServer()` | Refresh user data in background |

---

## Available Signals in AdminService

| Signal | Type | Description |
|--------|------|-------------|
| `stats` | `AdminStats \| null` | Dashboard statistics |
| `users` | `AdminUser[]` | All users list |
| `settings` | `AppSettings` | App settings |
| `auditLog` | `AuditLogEntry[]` | Audit log entries |
| `loading` | `boolean` | Loading state |
| `pendingUsers` | `AdminUser[]` | Computed: users awaiting approval |
| `approvedUsers` | `AdminUser[]` | Computed: approved users |

### AdminService Methods

| Method | Description |
|--------|-------------|
| `getStats()` | Fetch dashboard statistics |
| `getUsers()` | Fetch all users |
| `approveUser(userId)` | Approve a pending user |
| `rejectUser(userId)` | Reject and delete a user |
| `updateUserRole(userId, role)` | Change user role |
| `getSettings()` | Fetch app settings |
| `toggleClosedBetaMode(enabled)` | Enable/disable closed beta |
| `getAuditLog(action?, limit?)` | Fetch audit log entries |
