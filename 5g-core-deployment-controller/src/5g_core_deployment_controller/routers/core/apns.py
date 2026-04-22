"""APN management endpoints under /core."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from ...models import ApnCollectionReplaceRequest, ApnModel
from ...services import ApnService, ApnServiceError

router = APIRouter(prefix="/core", tags=["core", "apns"])

def _to_http_exception(error: ApnServiceError) -> HTTPException:
    """Convert service-level error to HTTPException."""
    return HTTPException(status_code=error.status_code, detail=error.detail)


@router.get("/apns", response_model=list[ApnModel])
async def list_apns(request: Request):
    """List all APNs from DNN_LIST."""
    service = ApnService(request.app)
    try:
        return await service.list_apns()
    except ApnServiceError as exc:
        raise _to_http_exception(exc)


@router.post("/apns", response_model=ApnModel, status_code=status.HTTP_201_CREATED)
async def create_apn(payload: ApnModel, request: Request):
    """Create one APN and persist DNN_LIST."""
    service = ApnService(request.app)
    try:
        return await service.create_apn(payload)
    except ApnServiceError as exc:
        raise _to_http_exception(exc)


@router.put("/apns/{name}", response_model=ApnModel)
async def replace_apn(name: str, payload: ApnModel, request: Request):
    """Replace one APN by name."""
    if payload.name != name:
        raise HTTPException(
            status_code=400,
            detail=f"Path name '{name}' must match body name '{payload.name}'",
        )

    service = ApnService(request.app)
    try:
        return await service.replace_apn(name, payload)
    except ApnServiceError as exc:
        raise _to_http_exception(exc)


@router.delete("/apns/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_apn(name: str, request: Request):
    """Delete one APN by name."""
    service = ApnService(request.app)
    try:
        await service.delete_apn(name)
    except ApnServiceError as exc:
        raise _to_http_exception(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/apns", response_model=list[ApnModel])
async def replace_apn_collection(payload: ApnCollectionReplaceRequest, request: Request):
    """Replace complete APN collection in one operation."""
    service = ApnService(request.app)
    try:
        return await service.replace_all_apns(payload.apns)
    except ApnServiceError as exc:
        raise _to_http_exception(exc)
