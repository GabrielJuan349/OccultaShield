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
Crea un archivo `.env` en la raíz de la carpeta `frontend` (basado en `.env.example` si existe):
```env
API_URL=http://localhost:8900/api/v1
```
*Nota: Asegúrate de que coincida con el puerto donde corre tu backend FastAPI.*

---

## 🏃 Ejecución en Desarrollo

Para lanzar el servidor de desarrollo con recarga automática:
```bash
bun run dev
# o
npm run start
```
La aplicación estará disponible en: `http://localhost:4200`

---

## 🧪 Flujo de Usuario en la App

El frontend está diseñado siguiendo un workflow lineal:

1.  **Dashboard / Upload**: Pantalla inicial para subir el video original.
2.  **Processing (SSE)**: Vista en tiempo real que muestra el progreso de la IA (detección y análisis legal). Verás cómo aparecen las detecciones de sujetos en el log.
3.  **Review Page (Human-in-the-Loop)**: 
    *   Aquí verás las **vulnerabilidades detectadas**.
    *   **Novedad Precision**: Gracias a YOLOv11, verás las siluetas exactas segmentadas.
    *   Puedes elegir entre `Blur`, `Pixelate`, `Mask` o `No Modify` para cada infracción.
4.  **Final Processing**: El sistema aplica los cambios físicos al video usando las máscaras de segmentación.
5.  **Download**: Descarga del video final anonimizado cumpliendo con el RGPD.

---

## 🏗️ Construcción para Producción

Si deseas generar los archivos estáticos optimizados:
```bash
bun run build
# o
npm run build
```
Los archivos se generarán en la carpeta `dist/frontend`.

---

## 🔍 Notas Técnicas
*   **Zoneless**: La app no usa `zone.js`. Toda la reactividad depende de **Signals**.
*   **SSE**: El estado del procesamiento se sincroniza vía `ProcessingSSEService`. Si recargas la página, el servicio se reconectará automáticamente y recuperará el estado actual del video.
*   **Directivas Modernas**: Se utiliza `@if`, `@for` y `@switch` (control flow nativo de Angular).
