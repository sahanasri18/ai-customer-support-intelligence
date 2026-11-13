"""Authenticated, task-specific prediction endpoints backed by saved models."""
from fastapi import APIRouter, Depends

from auth import get_current_user
from ml_predictor import model_status, predict
from schemas import PredictionInput, PredictionModelStatus, TaskPredictionResponse

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/status", response_model=PredictionModelStatus)
def get_prediction_status(_=Depends(get_current_user)):
    return model_status()


@router.post("/{task}", response_model=TaskPredictionResponse)
def predict_task(task: str, payload: PredictionInput, _=Depends(get_current_user)):
    fields = {
        "category": ("predicted_category", "category_confidence"),
        "priority": ("predicted_priority", "priority_confidence"),
        "sentiment": ("predicted_sentiment", "sentiment_confidence"),
    }
    if task not in fields:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown prediction task")
    result = predict(payload.subject, payload.description)
    value_key, confidence_key = fields[task]
    prediction = result[value_key]
    return TaskPredictionResponse(
        task=task,
        prediction=prediction,
        confidence=result[confidence_key],
        model_version=result["model_version"],
        status="available" if prediction is not None else "unavailable",
    )
