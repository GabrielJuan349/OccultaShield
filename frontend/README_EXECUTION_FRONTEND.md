# 🌐 Frontend Execution Guide (OccultaShield)

This document details how to run the OccultaShield user interface, built with **Angular v21 (Zoneless + Signals)** and a **Better Auth SSR Admin API**.

---

## 📋 Prerequisites

*   **Node.js**: v20.x or higher
*   **Package Manager**: **Bun** (recommended) or npm
*   **Backend**: Must be running (see `backend/README_EXECUTION_BACKEND.md`)

---

## 🛠️ Initial Configuration

### 1. Installing Dependencies
From the `frontend` folder:
```bash
bun install
# or
npm install
```

### 2. Environment Variables
Create a `.env` file in the `frontend` root:
```env
# Backend API
API_URL=http://localhost:8900/api/v1

# Better Auth Configuration
BETTER_AUTH_SECRET=your-secret-key-min-32-chars
BETTER_AUTH_URL=http://localhost:4200

# Email Configuration (for user approval notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=OccultaShield <noreply@occultashield.com>

# Database (SSR Admin API)
SURREAL_URL=http://localhost:8000
SURREAL_USER=root
SURREAL_PASS=root
SURREAL_NS=occultashield
SURREAL_DB=main
```

---

## 🏃 Running in Development

Launch the development server with SSR:
```bash
bun run dev
```

The application will be available at: **http://localhost:4200**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                 ANGULAR v21 CLIENT                       │  │
│   │   • Zoneless (no zone.js)                               │  │
│   │   • Signals for reactivity                              │  │
│   │   • Standalone components                               │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                 EXPRESS SSR SERVER                       │  │
│   │   • Server-side rendering                               │  │
│   │   • Better Auth integration                             │  │
│   │   • Admin API endpoints                                 │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│   │   SurrealDB  │ │   Backend    │ │    SMTP      │           │
│   │  (User data) │ │   FastAPI    │ │  (Emails)    │           │
│   └──────────────┘ └──────────────┘ └──────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Administration Panel

OccultaShield includes a protected admin area at `/admin`:

### Dashboard (`/admin/dashboard`)
- Processing statistics
- Recent activity (Audit Log)
- System health status

### User Management (`/admin/users`)
- View all registered users
- Approve/Reject registration requests
- Change user roles:
  - `user` - Standard user
  - `researcher` - Academic/research access
  - `agency` - Enterprise/agency access
  - `admin` - Full admin privileges
- Send approval/rejection emails

### Settings (`/admin/settings`)
- Enable/Disable **Closed Beta Mode**
- Configure email templates
- System configuration

---

## 🧪 User Flow in the App

### 1. Registration Flow
```
User registers → Selects usage type → Email confirmation sent
                      │
                      ▼
            [If Beta Mode Active]
                      │
                      ▼
         Admin reviews in /admin/users
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
        APPROVE             REJECT
            │                   │
            ▼                   ▼
    Access granted      Rejection email
       email sent           sent
```

### 2. Video Processing Flow
```
Upload Video → Detection → Verification → Review Page → Download
                  │            │              │
                  ▼            ▼              ▼
             YOLOv11-seg   Temporal     Human-in-the-Loop
             + Kornia      Consensus    Decision Panel
```

### 3. Review Page Features

| Feature | Description |
|---------|-------------|
| **Detection List** | All detections with thumbnails |
| **Bounding Box Overlay** | Visual preview on video |
| **Action Selector** | blur / pixelate / mask / no_modify |
| **Legal Context** | GDPR articles and AI reasoning |
| **Batch Actions** | Apply same effect to all |

---

## 📱 Key Pages

| Route | Description | Auth Required |
|-------|-------------|---------------|
| `/` | Landing page | No |
| `/auth/login` | User login | No |
| `/auth/register` | User registration | No |
| `/dashboard` | User dashboard | Yes |
| `/upload` | Video upload | Yes |
| `/review/:videoId` | Detection review | Yes |
| `/history` | Processing history | Yes |
| `/admin/*` | Admin panel | Admin role |

---

## 🎨 UI Components

### Toast Notifications
Real-time visual notifications for:
- Upload progress
- Processing status
- Admin actions
- Error messages

### Progress Indicators
- SSE-based real-time updates
- Phase progress bars
- Detection count updates

### Better Auth Integration
- Session management
- Role-based access control
- Email verification flow

---

## 🏗️ Building for Production

```bash
bun run build
```

Files will be generated in `dist/`:
- `dist/frontend/browser/` - Client-side assets
- `dist/frontend/server/` - SSR server

### Production Execution
```bash
node dist/frontend/server/server.mjs
```

Or with PM2:
```bash
pm2 start dist/frontend/server/server.mjs --name occultashield-frontend
```

---

## 🔧 Configuration Files

### `angular.json`
- Build targets (development, production)
- SSR configuration
- Asset optimization

### `proxy.conf.js`
- Development proxy to backend
- API route forwarding

### `tsconfig.json`
- TypeScript configuration
- Strict mode enabled

---

## 🔍 Technical Notes

### Zoneless Architecture
- No `zone.js` dependency
- Explicit change detection via Signals
- Better performance and bundle size

### Signals
```typescript
// Example Signal usage
videoProgress = signal<number>(0);
detections = signal<Detection[]>([]);

// Computed values
totalDetections = computed(() => this.detections().length);
```

### SSR Admin API
- Admin logic runs on Express server
- Direct SurrealDB access (no backend needed for admin)
- Secure: credentials never exposed to client

---

## 🐛 Troubleshooting

### "Cannot connect to backend"
```bash
# Check if backend is running
curl http://localhost:8900/health

# Verify proxy configuration in proxy.conf.js
```

### "Email not sending"
```bash
# Verify SMTP credentials in .env
# Check spam folder
# For Gmail, use App Password (not regular password)
```

### "SSR hydration mismatch"
```bash
# Clear browser cache
# Restart dev server
bun run dev
```

---

## 📚 References

- **Angular v21**: https://angular.dev/
- **Better Auth**: https://www.better-auth.com/
- **Bun**: https://bun.sh/
- **SurrealDB**: https://surrealdb.com/docs/
