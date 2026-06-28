from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health", tags=["health"])
async def health():
    return JSONResponse({"status": "ok", "service": "helix-api"})
