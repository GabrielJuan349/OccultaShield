from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from contextlib import asynccontextmanager
from db.surreal_conn import SurrealConn
from auth.auth_middleware import AuthMiddleware

from api.v1.router import api_router

# Global connection instance
# Note: We rely on core.dependencies for injection, but middleware needs it too.
# The middleware expects a SurrealConn instance.
surreal_conn = SurrealConn()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await surreal_conn.getting_db()
    
    yield
    
    # Shutdown
    await surreal_conn.close()
    print("Database connection closed")

    
app = FastAPI(
    title="OccultaShield API",
    version="1.0.0",
    lifespan=lifespan
)

# IMPORTANTE: CORS debe ir ANTES del middleware de autenticación
# para que las preflight requests (OPTIONS) sean manejadas correctamente
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://localhost:4201",
        "http://localhost:4000",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:4201",
        "http://127.0.0.1:4000",
        "http://mise-ralph.uab.cat:4200",
        "http://mise-ralph.uab.cat:4201",
        "http://mise-ralph.uab.cat:8980"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Configurar middleware de autenticación (DESPUÉS de CORS)
app.add_middleware(AuthMiddleware, surreal_conn=surreal_conn)

# Inicializar auth service (si se usa globalmente)
# auth_service = AuthService(surreal_conn)  <-- Removed per user request

# Include API Router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"status": "ok", "service": "OccultaShield Backend"}


if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 8980))
    uvicorn.run("main:app", host=host, port=port, reload=True)
