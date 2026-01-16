<div align="center">

# 🌐 OccultaShield Frontend

### High-Fidelity SSR Interface and Administration Panel (Angular v21)

[![Angular](https://img.shields.io/badge/Angular-v21.0-DD0031?style=for-the-badge&logo=angular&logoColor=white)](https://angular.io/)
[![Bun](https://img.shields.io/badge/Bun-1.3.1-000000?style=for-the-badge&logo=bun&logoColor=white)](https://bun.sh/)
[![Better-Auth](https://img.shields.io/badge/Auth-Better--Auth-blueviolet?style=for-the-badge)](https://better-auth.com)
[![Zoneless](https://img.shields.io/badge/Architecture-Zoneless-blue?style=for-the-badge)](https://angular.dev)

**Instant and secure user experience with Server-Side Rendering (SSR), Signals, and advanced administrative management.**

</div>

---

## 🚀 Overview

The OccultaShield frontend transcends the conventional video player. It is a complete **Compliance Suite**. Built with the latest technology available in 2025 (Angular v21), it offers a smooth, reactive, and secure experience for making critical privacy decisions.

Its **Zoneless** architecture ensures that even with hundreds of detections on screen (Bounding Boxes), the interface maintains 60 FPS without freezing.

---

## ✨ Advanced Technical Features

### 1. "Bleeding Edge" Architecture (Zoneless + SSR)
*   **Goodbye Zone.js**: We have eliminated the dependency on `zone.js` for change detection. Now, the UI reacts to atomic state changes through **Signals**, drastically reducing CPU and memory usage.
*   **Server-Side Rendering (SSR)**: Thanks to **Bun** and the Express adapter, the application renders on the server before reaching the client, ensuring near-instant load times (`LCP`).
*   **Non-destructive Hydration**: Angular rehydrates the client state without flickering, allowing immediate interaction.

### 2. Administration Panel and Security (`/admin`)
*   **Role-Based Access Control (RBAC)**: Granular permission system.
    *   *Admins*: Approve accounts, view global metrics, access audit logs.
    *   *Users*: Only see their own videos.
*   **"Closed Beta" System**: Registration flow with manual approval. New users remain in `Pending` status until validated.
*   **Immutable Audit Log**: Every administrative action (approve user, change settings) is recorded and signed in the system.

### 3. Review Experience (Review Room)
*   **Real-time SSE Streaming**: Continuous connection with the backend to show detection progress frame by frame.
*   **Secure Player**:
    *   **Anti-Screenshot**: The UI detects screenshot keyboard shortcuts and obfuscates sensitive content.
    *   **Watermarks**: Dynamic overlay with the viewer's user ID to trace leaks.
    *   **Violation Navigation**: Interactive timeline marking the exact moments of GDPR violation.

---

## 🏃 Development Guide

### 1. Requirements
*   [Bun](https://bun.sh) v1.1+ installed globally.
*   Node.js v20+ (optional, Bun replaces it in most tasks).
*   OccultaShield Backend running on port `8980`.

### 2. Installing Dependencies
We use Bun for ultra-fast installation (10x faster than npm).
```bash
cd frontend
bun install
```

### 3. Environment Configuration (`.env`)
```bash
cp .env.example .env
nano .env
```
**Critical Variables:**
*   `API_URL`: Backend URL (e.g., `http://localhost:8980/api/v1`).
*   `BETTERAUTH_SECRET`: Secret key for signing sessions.
*   `SMTP_*`: Configuration for sending transactional emails (invitations, approvals).

### 4. Running (Development Mode)
Start the development server with Hot Module Replacement (HMR).
```bash
bun run dev
```
Access `http://localhost:4200`. The application will automatically proxy `/api` requests to the backend if using the default configuration.

### 5. Build and Production (SSR)
For deployment in a real environment:
```bash
# Build the application (generates dist/occultashield/browser and server)
bun run build

# Serve with the Node.js/Bun SSR engine
bun run serve:ssr
```
The application will be available at `http://localhost:4000` (or `PORT` defined in env).

---

## 📂 Directory Architecture (Subpath Imports)

The project uses a modern alias system (`#`) defined in `tsconfig.json` to maintain strict modularity:

*   `#components/*`: **UI Kit**. Pure presentation components (ViolationCard, ProgressBar, Header). Standalone and without complex business logic.
*   `#pages/*`: **Views**. Routed components that orchestrate logic (UploadPage, ReviewPage, AdminPage).
*   `#services/*`: **Data Layer**. Injectable services, HTTP clients, and state stores (Signals).
*   `#server/*`: **SSR Backend**. Code that **only** runs on the server (Admin API Routes, Express configuration, Auth Handlers).
*   `#interface/*`: **Types**. Shared TypeScript contracts.

---

## 🔒 Security Details (Frontend)
*   **Auth Interceptor**: Automatically injects session tokens in headers for API requests.
*   **Error Interceptor**: Globally handles 401/403 responses, redirecting to login or refreshing sessions.
*   **Sanitization**: All rendered HTML content goes through `DomSanitizer` to prevent XSS.
