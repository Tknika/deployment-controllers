"""
MongoDB service with proper dependency injection pattern.
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

logger = logging.getLogger(__name__)


class MongoDBService:
    """MongoDB service for subscriber management with connection pooling and index management."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Initialize MongoDB service with connection parameters.
        
        Args:
            host: MongoDB hostname (e.g., 'mongo', 'localhost')
            port: MongoDB port (typically 27017)
            database: Database name (e.g., 'open5gs')
            user: Optional username for authentication
            password: Optional password for authentication
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.subscribers_collection_name = "subscribers"
        
        self._client: Optional[AsyncIOMotorClient] = None
        self._indexes_initialized = False

    def _build_uri(self) -> str:
        """Build MongoDB connection URI."""
        if self.user and self.password:
            return f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/"
        return f"mongodb://{self.host}:{self.port}/"

    def get_client(self) -> AsyncIOMotorClient:
        """Get or create MongoDB client instance (singleton pattern)."""
        if self._client is None:
            uri = self._build_uri()
            logger.info(f"Connecting to MongoDB at {self.host}:{self.port}")
            self._client = AsyncIOMotorClient(uri)
        return self._client

    async def _ensure_indexes(self, collection: AsyncIOMotorCollection) -> None:
        """Ensure required indexes exist on collection."""
        if self._indexes_initialized:
            return
        try:
            await collection.create_index("imsi", unique=True)
            self._indexes_initialized = True
            logger.info("Created unique index on subscribers.imsi")
        except Exception as exc:
            logger.warning(f"Failed to create index on subscribers.imsi: {exc}")

    async def get_subscriber_collection(self) -> AsyncIOMotorCollection:
        """Get subscribers collection with guaranteed indexes."""
        client = self.get_client()
        collection = client[self.database][self.subscribers_collection_name]
        await self._ensure_indexes(collection)
        return collection

    def close(self) -> None:
        """Close MongoDB connection."""
        if self._client is not None:
            self._client.close()
            logger.info("Closed MongoDB connection")
            self._client = None
