import surrealdb as sr
from dotenv import load_dotenv
import os

# Cargar las variables del archivo .env
load_dotenv()

class SurrealConn:
    def __init__(self):
        self.db = None
        self.host = os.environ.get('SURREALDB_HOST') # Use get but check later or enforce?
        # User said "eliminalo". Strict env usually means fail storage.
        if not os.getenv("SURREALDB_HOST"):
             # Or rely on os.environ[] to raise KeyError
             pass
             
        self.host = os.environ["SURREALDB_HOST"]
        self.port = os.environ["SURREALDB_PORT"]
        self.user = os.environ["SURREALDB_USER"]
        self.password = os.environ["SURREALDB_PASS"]
    
    async def connect(self):
        """Conecta a la base de datos de forma asíncrona"""
        self.db = sr.AsyncSurreal(f"ws://{self.host}:{self.port}/rpc")
        try:
            await self.db.signin({
                "username": self.user,
                "password": self.password,
            })
            print("Successfully connected to SurrealDB")
        except Exception as e:
            print(f"Error connecting to SurrealDB: {e}")
            raise

    
    async def getting_db(self, database_name: str):
        """Selecciona el namespace y base de datos"""
        if not self.db:
            await self.connect()
        namespace = os.environ["SURREALDB_NAMESPACE"]
        item = os.environ["SURREALDB_ITEM"] # DB Name
        await self.db.use(namespace, database_name or item)
        return self.db
    
    async def close(self):
        """Cierra la conexión"""
        if self.db:
            await self.db.close()