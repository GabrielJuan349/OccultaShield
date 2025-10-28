from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from contextlib import asynccontextmanager
from surreal_conn import SurrealConn
from auth import AuthMiddleware, AuthService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Conectar a la base de datos
    global surreal_conn
    surreal_conn = SurrealConn()
    await surreal_conn.connect()
    
    yield  # Aquí la aplicación está corriendo
    
    # Shutdown: Cerrar la conexión
    await surreal_conn.close()
    print("Database connection closed")

    
app = FastAPI(lifespan=lifespan)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Permite todos los headers
    options_success_status=204,
)

# Configurar middleware de autenticación
app.add_middleware(AuthMiddleware, surreal_conn=surreal_conn)
# Inicializar el servicio de autenticación
auth_service = AuthService(surreal_conn)

# print("Using database:", db)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/auth/login")
def login():
    return {"status": "User logged in"}
@app.post("/auth/register")
def register():
    return {"status": "User registered"}
@app.post("/osd/in")
def enter_video():
    return {"status": "Video entered"}
@app.post("/osd/processed")
def processed():
    try:
        # Logic to mark quest as done
        return {"status": "Quest marked as done"}
    except Exception as e:
        return {"error": str(e)}
@app.post("/osd/quest_done")
def quest_done():
    try:
        # Logic to mark quest as done
        return {"status": "Quest marked as done"}
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/osd/exit")
def exit_video():
    return {"status": "Video exited"}
    
if __name__ == "__main__":

    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", 8900))
    uvicorn.run("main:app", host=host, port=port, reload=True)
