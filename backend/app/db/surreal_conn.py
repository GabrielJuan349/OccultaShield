import surrealdb as sr
from dotenv import load_dotenv
import os
import logging
import asyncio

# Cargar las variables del archivo .env
load_dotenv()

logger = logging.getLogger(__name__)

class SurrealConn:
    def __init__(self):
        self.db = None
        self._connected = False
        self._lock = asyncio.Lock()
        # Soporte para URL completa o componentes individuales de Docker
        self.url = os.getenv('SURREALDB_URL')
        self.host = os.getenv('SURREALDB_HOST', 'localhost')
        self.port = os.getenv('SURREALDB_PORT', '8000')
        self.user = os.getenv('SURREALDB_USER', 'root')
        self.password = os.getenv('SURREALDB_PASS', 'root')

        if not self.url:
            self.url = f"ws://{self.host}:{self.port}/rpc"

    async def _ensure_connected(self):
        """Verifica que la conexión está activa, reconecta si es necesario."""
        if self.db and self._connected:
            try:
                # Test connection with a simple query
                await self.db.query("RETURN 1")
                return True
            except Exception as e:
                logger.warning(f"Connection test failed: {e}, reconnecting...")
                self._connected = False
                self.db = None
        return False

    async def connect(self):
        """Conecta a la base de datos de forma asíncrona"""
        async with self._lock:
            # Double-check after acquiring lock
            if await self._ensure_connected():
                return

            logger.info(f"Connecting to SurrealDB at {self.url}")
            self.db = sr.AsyncSurreal(self.url)
            try:
                await self.db.signin({
                    "username": self.user,
                    "password": self.password,
                })
                self._connected = True
                print(f"✅ Successfully connected to SurrealDB at {self.url}")
            except Exception as e:
                print(f"❌ Error connecting to SurrealDB: {e}")
                self._connected = False
                self.db = None
                raise

    async def getting_db(self, database_name: str = None):
        """Selecciona el namespace y base de datos, reconectando si es necesario."""
        # Ensure connection is active
        if not await self._ensure_connected():
            await self.connect()

        namespace = os.getenv("SURREALDB_NAMESPACE", "test")
        default_db = os.getenv("SURREALDB_DB", "occultashield")

        target_db = database_name or default_db

        try:
            await self.db.use(namespace, target_db)
            logger.debug(f"Using namespace: {namespace}, database: {target_db}")
        except Exception as e:
            logger.error(f"Error selecting namespace/database: {e}")
            # Connection might be broken, try reconnecting
            self._connected = False
            await self.connect()
            await self.db.use(namespace, target_db)

        return self.db

    async def close(self):
        """Cierra la conexión"""
        async with self._lock:
            if self.db:
                try:
                    await self.db.close()
                    print("SurrealDB connection closed")
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
                finally:
                    self.db = None
                    self._connected = False