import surrealdb as sr
from dotenv import load_dotenv
import os

# Cargar las variables del archivo .env
load_dotenv()

class SurrealConn:
    def __init__(self):
        self.db = None
        self.host = os.getenv('SURREALDB_HOST', 'localhost')
        self.port = os.getenv('SURREALDB_PORT', '8000')
        self.user = os.getenv("SURREALDB_USER")
        self.password = os.getenv("SURREALDB_PASS")
    
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
        namespace = os.getenv("SURREALDB_NAMESPACE", "test")
        await self.db.use(namespace, database_name)
        return self.db
    
    async def close(self):
        """Cierra la conexión"""
        if self.db:
            await self.db.close()