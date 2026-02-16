"""
Servicio de conexión a MongoDB para DrON Topografía
"""
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
mongo_url = os.environ.get("MONGO_URL")
db_name = os.environ.get("DB_NAME", "dron_topografia")

if not mongo_url:
    raise ValueError("MONGO_URL environment variable is not set")

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Collections
usuarios_collection = db.usuarios
proyectos_collection = db.proyectos
vuelos_collection = db.vuelos
avances_collection = db.avances_semanales
solicitudes_collection = db.solicitudes_vuelo

logging.info(f"Connected to MongoDB database: {db_name}")


async def get_db():
    """Dependency to get database instance"""
    return db


async def init_db():
    """Initialize database with indexes"""
    # Create indexes
    await usuarios_collection.create_index("email", unique=True)
    await proyectos_collection.create_index("nombre")
    await vuelos_collection.create_index("proyecto_id")
    await avances_collection.create_index([("proyecto_id", 1), ("semana", 1)])
    await solicitudes_collection.create_index("cliente_id")
    logging.info("Database indexes created")


async def cleanup_obsolete_collections():
    """Remove obsolete collections (like 'users' which was replaced by 'usuarios')"""
    try:
        collections = await db.list_collection_names()
        if "users" in collections:
            await db.users.drop()
            logging.info("Dropped obsolete 'users' collection")
            return True
    except Exception as e:
        logging.error(f"Error cleaning up obsolete collections: {e}")
    return False
