"""
4g Core Deployment Controller
"""

import logging
import os
import pathlib
import uvicorn

from base_deployment_controller import AppBuilder
from .routers.core import router as core_router
from .routers.core import subscribers
from .services import MongoDBService

# Obtener la ruta raíz del proyecto (tres niveles arriba desde main.py)
# En desarrollo: apunta a la raíz del proyecto para acceder a data/
# En producción: las rutas vendrán de variables de entorno
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.resolve()

# Configuration env vars
# En producción, estas variables se deben definir con rutas absolutas o montajes
COMPOSE_FILE = os.getenv("COMPOSE_FILE", str(PROJECT_ROOT / "data" / "compose.yaml"))
ENV_FILE = os.getenv("ENV_FILE", str(PROJECT_ROOT / "data" / ".env"))
API_PORT = int(os.getenv("API_PORT", "8000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# MongoDB configuration
MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_DB = os.getenv("MONGO_DB", "open5gs")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize MongoDB service
mongodb_service = MongoDBService(
    host=MONGO_HOST,
    port=MONGO_PORT,
    database=MONGO_DB,
    user=MONGO_USER,
    password=MONGO_PASSWORD,
)

# Inject MongoDB service into routers
subscribers.set_mongodb_service(mongodb_service)

builder = AppBuilder(COMPOSE_FILE, ENV_FILE)
app = builder.register_router(core_router).build()

if __name__ == "__main__":
    logger.info(f"Starting 4G Core Deployment Controller on http://0.0.0.0:{API_PORT}")
    logger.info(f"Log level set to: {LOG_LEVEL}")
    # En desarrollo desde raíz del proyecto, usa la ruta completa del módulo
    uvicorn.run("src.4g_core_deployment_controller.main:app", host="0.0.0.0", port=API_PORT, reload=True)