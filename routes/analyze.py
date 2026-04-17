from fastapi import APIRouter, HTTPException, Depends
from auth import get_current_user
from logic.emotion_detector import (
    predict_emotions,
    get_dominant_emotion,
    is_needs_help
)

router = APIRouter(prefix="/analyze", tags=["Analyze"])


@router.post("/text")
async def analyze_text(
    req: dict,
    current_user: dict = Depends(get_current_user)
):
    text = req.get("text", "")

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Text is required"
        )

    emotions = predict_emotions(text)
    dominant = get_dominant_emotion(text)
    needs_help = is_needs_help(text)

    return {
        "text": text,
        "emotions": emotions,
        "dominant_emotion": dominant,
        "needs_help": needs_help,
        "message": "Help recommended" if needs_help else "Looking good"
    }