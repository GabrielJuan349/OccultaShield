const PROXY_CONFIG = {
    "/api/v1": {
        target: "http://localhost:8980",
        secure: false,
        logLevel: "debug",
        changeOrigin: true,
        // Configuración especial para SSE (Server-Sent Events)
        onProxyRes: function (proxyRes, req, res) {
            // Si la request es al endpoint de progress (SSE)
            if (req.url.includes('/progress')) {
                console.log('🔥 [PROXY] SSE Request detectada:', req.url);
                // Deshabilitar buffering para SSE
                proxyRes.headers['Cache-Control'] = 'no-cache, no-transform';
                proxyRes.headers['X-Accel-Buffering'] = 'no';
                proxyRes.headers['Connection'] = 'keep-alive';
                console.log('✅ [PROXY] Headers SSE configurados');
            }
        }
    },
    "/api": {
        target: "http://localhost:4201",
        secure: false,
        logLevel: "debug",
        changeOrigin: true
    }
};

module.exports = PROXY_CONFIG;
