# 🌐 Guía de Ejecución del Frontend (OccultaShield)

Este documento detalla cómo poner en marcha la interfaz de usuario de OccultaShield, construida con **Angular v21 (Zoneless + Signals)**.

---

## 📋 Requisitos Previos

*   **Node.js**: v20.x o superior.
*   **Gestor de paquetes**: Se recomienda **Bun** (usado en el desarrollo) o **npm**.
*   **Backend**: Debe estar en ejecución para que el frontend pueda procesar videos (ver `backend/README_EXECUTION_BACKEND.md`).

---

## 🛠️ Configuración Inicial

### 1. Instalación de dependencias
Desde la carpeta `frontend`, ejecuta:
```bash
bun install
# o
npm install
```

### 2. Variables de Entorno
Crea un archivo `.env` en la raíz de la carpeta `frontend`:
```env
API_URL=http://localhost:8900/api/v1
# Configuración de Email (para aprobación de usuarios)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASS=tu-app-password
SMTP_FROM=OccultaShield <noreply@occultashield.com>
```

---

## 🏃 Ejecución en Desarrollo

Para lanzar el servidor de desarrollo (incluye el SSR para la Admin API):
```bash
bun run dev
```
La aplicación estará disponible en: `http://localhost:4200`

---

## 🛡️ Panel de Administración

OccultaShield incluye un área protegida para administradores en `/admin`:

- **Dashboard**: Resumen de estadísticas y actividad reciente (Audit Log).
- **Gestión de Usuarios**: Aprobación/Rechazo de solicitudes de registro y cambio de roles.
- **Configuración**: Activación/Desactivación del "Modo Beta Cerrado".

---

## 🧪 Flujo de Usuario en la App

1.  **Registro**: El usuario se registra y selecciona su tipo de uso (Individual, Investigador, Agencia).
2.  **Aprobación (Admin)**: 
    *   Si el Modo Beta está activo, el usuario recibe un email de confirmación de registro.
    *   El admin aprueba al usuario desde `/admin/users`.
    *   El usuario recibe un segundo email confirmando su acceso.
3.  **Upload & Process**: El usuario sube y analiza su video.
4.  **Review Page (Human-in-the-Loop)**: Selección de efectos sobre siluetas segmentadas por YOLOv11.
5.  **Download**: Obtención del video final.

---

## 🏗️ Construcción para Producción

```bash
bun run build
```
Los archivos se generarán en la carpeta `dist/`. La ejecución en producción requiere el servidor SSR para manejar la autenticación y la API de administración.

---

## 🔍 Notas Técnicas
*   **Zoneless + Signals**: Reactividad moderna sin dependencias de `zone.js`.
*   **SSR Admin API**: La lógica de administración corre en el servidor Express que sirve la app, permitiendo acceso directo y seguro a SurrealDB.
*   **Toast Notifications**: Sistema de avisos visuales en tiempo real para confirmar acciones administrativas.
