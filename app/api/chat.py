from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.chat import get_chat_response

router = APIRouter(prefix="/chat", tags=["Chat"])


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default", max_length=64)


class MessageResponse(BaseModel):
    response: str
    pii_detected: bool
    session_id: str


@router.post("/", response_model=MessageResponse, summary="Send a message to URAAN Safe Voice")
async def chat(request: MessageRequest):
    result = await get_chat_response(request.message)
    return MessageResponse(
        response=result["response"],
        pii_detected=result["pii_detected"],
        session_id=request.session_id,
    )
