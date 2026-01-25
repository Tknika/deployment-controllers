"""
Subscriber management endpoints under /core.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from ...models import SubscriberSchema
from ...services import MongoDBService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core", tags=["core", "subscribers"])

# Service instance injected from main.py during startup
_mongodb_service: Optional[MongoDBService] = None


def set_mongodb_service(service: MongoDBService) -> None:
    """Initialize MongoDB service for this router module."""
    global _mongodb_service
    _mongodb_service = service


async def get_subscriber_collection() -> AsyncIOMotorCollection:
    """FastAPI dependency to provide subscriber collection."""
    if _mongodb_service is None:
        raise RuntimeError("MongoDB service not initialized")
    return await _mongodb_service.get_subscriber_collection()


@router.get("/subscribers", response_model=List[SubscriberSchema])
async def get_subscribers(
    name: Optional[str] = None,
    sst: Optional[int] = None,
    sd: Optional[str] = None,
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    collection: AsyncIOMotorCollection = Depends(get_subscriber_collection),
):
    """List subscribers with optional filters."""
    query: dict = {}

    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    if sst is not None:
        slice_filter: dict = {"sst": sst}
        if sd:
            slice_filter["sd"] = sd
        query["slice"] = {"$elemMatch": slice_filter}

    cursor = collection.find(query).skip(offset).limit(limit)
    subscribers: list[SubscriberSchema] = []
    async for document in cursor:
        subscribers.append(SubscriberSchema.model_validate(document))

    logger.info(
        f"Retrieved {len(subscribers)} subscribers with filters name={name} sst={sst} sd={sd} limit={limit} offset={offset}"
    )
    return subscribers


@router.post("/subscribers", response_model=SubscriberSchema, status_code=status.HTTP_201_CREATED)
async def create_subscriber(
    subscriber_data: SubscriberSchema,
    collection: AsyncIOMotorCollection = Depends(get_subscriber_collection),
):
    """Create a new subscriber."""
    subscriber_dict = subscriber_data.model_dump(by_alias=True, exclude={"id"}, exclude_none=True)
    
    try:
        result = await collection.insert_one(subscriber_dict)
        subscriber_dict["_id"] = str(result.inserted_id)
        created_subscriber = SubscriberSchema.model_validate(subscriber_dict)
        logger.info(f"Created subscriber {subscriber_data.imsi}")
        return created_subscriber
    except DuplicateKeyError:
        logger.warning(f"Duplicate IMSI conflict while creating {subscriber_data.imsi}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subscriber with IMSI {subscriber_data.imsi} already exists",
        )


@router.delete("/subscribers/{imsi}")
async def delete_subscriber(
    imsi: str,
    collection: AsyncIOMotorCollection = Depends(get_subscriber_collection),
):
    """Delete a subscriber by IMSI."""
    delete_result = await collection.delete_one({"imsi": imsi})

    if delete_result.deleted_count == 1:
        logger.info(f"Deleted subscriber {imsi}")
        return {"status": "success", "message": f"Subscriber {imsi} deleted"}

    logger.warning(f"Subscriber {imsi} not found for deletion")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Subscriber with IMSI {imsi} not found",
    )


@router.put("/subscribers/{imsi}")
async def update_subscriber(
    imsi: str,
    updated_data: SubscriberSchema,
    collection: AsyncIOMotorCollection = Depends(get_subscriber_collection),
):
    """Replace subscriber data by IMSI, enforcing path IMSI."""
    update_dict = updated_data.model_dump(by_alias=True, exclude_none=True)
    update_dict["imsi"] = imsi

    try:
        result = await collection.replace_one({"imsi": imsi}, update_dict)
    except DuplicateKeyError:
        logger.warning(f"Duplicate IMSI conflict while updating {imsi}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subscriber IMSI {imsi} conflicts with an existing subscriber",
        )

    if result.matched_count == 0:
        logger.warning(f"Subscriber {imsi} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscriber with IMSI {imsi} not found",
        )

    logger.info(f"Updated subscriber {imsi}")
    return {"status": "success", "message": f"Subscriber {imsi} updated"}
