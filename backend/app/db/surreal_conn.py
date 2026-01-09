import surrealdb as sr
from dotenv import load_dotenv
import os
import logging

# Cargar las variables del archivo .env
load_dotenv()

logger = logging.getLogger(__name__)

class SurrealConn:
    def __init__(self):
        self.db = None
        # Soporte para URL completa o componentes individuales de Docker
        self.url = os.getenv('SURREALDB_URL')
        self.host = os.getenv('SURREALDB_HOST', 'localhost')
        self.port = os.getenv('SURREALDB_PORT', '8000')
        self.user = os.getenv('SURREALDB_USER', 'root')
        self.password = os.getenv('SURREALDB_PASS', 'root')
        
        if not self.url:
            self.url = f"ws://{self.host}:{self.port}/rpc"
    
    async def connect(self):
        """Conecta a la base de datos de forma asíncrona"""
        logger.info(f"Connecting to SurrealDB at {self.url}")
        self.db = sr.AsyncSurreal(self.url)
        try:
            await self.db.signin({
                "username": self.user,
                "password": self.password,
            })
            print(f"Successfully connected to SurrealDB at {self.url}")
        except Exception as e:
            print(f"Error connecting to SurrealDB: {e}")
            raise
    
    async def getting_db(self, database_name: str = None):
        """Selecciona el namespace y base de datos"""
        if not self.db:
            await self.connect()
        
        namespace = os.getenv("SURREALDB_NAMESPACE", "test")
        default_db = os.getenv("SURREALDB_DB", "occultashield")
        
        target_db = database_name or default_db
        
        await self.db.use(namespace, target_db)
        return self.db
    
    async def close(self):
        """Cierra la conexión"""
        if self.db:
            await self.db.close()
            print("SurrealDB connection closed")