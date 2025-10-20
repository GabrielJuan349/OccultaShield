from fastapi import FastAPI
import os
import uvicorn
from contextlib import asynccontextmanager
from surreal_conn import SurrealConn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Conectar a la base de datos
    global surreal_conn
    surreal_conn = SurrealConn()
    await surreal_conn.connect()
    await surreal_conn.getting_db("knowledge_graph")
    print("Database connected successfully")
    
    yield  # Aquí la aplicación está corriendo
    
    # Shutdown: Cerrar la conexión
    await surreal_conn.close()
    print("Database connection closed")

    
app = FastAPI(lifespan=lifespan)
# print("Using database:", db)

@app.get("/")
def read_root():
    return {"Hello": "World"}

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
