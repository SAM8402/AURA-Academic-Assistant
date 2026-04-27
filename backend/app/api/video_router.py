from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.video.summary_service import video_summary_service

router = APIRouter()

class VideoRequest(BaseModel):
    url: str

@router.post("/summarize")
async def summarize_video_endpoint(request: VideoRequest):
    result = await video_summary_service.summarize_video(request.url)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result