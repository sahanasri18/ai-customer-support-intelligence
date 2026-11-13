"""Load local ML pipelines and return only predictions the artifacts support."""
import json
import logging
from pathlib import Path
from typing import Any

import joblib


logger = logging.getLogger(__name__)
ML_DIR = Path(__file__).resolve().parent.parent / "ml" / "models"

_category_model = None
_priority_model = None
_sentiment_model = None
_model_version = None
_manifest: dict[str, Any] = {}


def _load_models() -> None:
    global _category_model, _priority_model, _sentiment_model, _model_version, _manifest
    manifest_path = ML_DIR / "model_manifest.json"
    if manifest_path.is_file():
        try:
            _manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            _model_version = _manifest.get("model_version")
        except (OSError, ValueError) as exc:
            logger.warning("Could not read model manifest (%s)", type(exc).__name__)

    version_path = ML_DIR / "model_version.txt"
    if version_path.is_file() and not _model_version:
        try:
            _model_version = version_path.read_text(encoding="utf-8").strip() or None
        except OSError as exc:
            logger.warning("Could not read model version (%s)", type(exc).__name__)

    for task, filename in (
        ("category", "category_pipeline.joblib"),
        ("priority", "priority_pipeline.joblib"),
        ("sentiment", "sentiment_pipeline.joblib"),
    ):
        artifact = ML_DIR / filename
        if not artifact.is_file():
            continue
        try:
            model = joblib.load(artifact)
            if task == "category":
                _category_model = model
            elif task == "priority":
                _priority_model = model
            else:
                _sentiment_model = model
            logger.info("%s model loaded", task.capitalize())
        except Exception as exc:
            logger.warning("Could not load %s model (%s)", task, type(exc).__name__)

    if not any((_category_model, _priority_model, _sentiment_model)):
        _model_version = None


_load_models()


def model_status() -> dict[str, Any]:
    declared = _manifest.get("models", {})
    runtime_models = {
        "category": _category_model,
        "priority": _priority_model,
        "sentiment": _sentiment_model,
    }
    models = {}
    for task, model in runtime_models.items():
        entry = declared.get(task, {})
        models[task] = {
            "available": model is not None,
            "confidence_available": bool(model is not None and hasattr(model, "predict_proba")),
            "reason": None if model is not None else entry.get("reason", "No trained model artifact is installed."),
        }
    return {
        "model_version": _model_version,
        "trained_at_utc": _manifest.get("trained_at_utc"),
        "source_dataset": _manifest.get("source_dataset"),
        "models": models,
        "urgent_detection": {
            "available": True,
            "method": "keyword rules",
            "confidence_available": False,
        },
    }


def _predict_with_confidence(model, text: str) -> tuple[str, float | None]:
    prediction = str(model.predict([text])[0])
    confidence = None
    if hasattr(model, "predict_proba"):
        confidence = round(float(max(model.predict_proba([text])[0])), 4)
    return prediction, confidence


def predict(subject: str, description: str) -> dict[str, Any]:
    text = f"{subject} {description}"
    result: dict[str, Any] = {
        "predicted_category": None,
        "category_confidence": None,
        "predicted_priority": None,
        "priority_confidence": None,
        "predicted_sentiment": None,
        "sentiment_confidence": None,
        "model_version": _model_version,
    }
    for task, model, label_key, confidence_key in (
        ("category", _category_model, "predicted_category", "category_confidence"),
        ("priority", _priority_model, "predicted_priority", "priority_confidence"),
        ("sentiment", _sentiment_model, "predicted_sentiment", "sentiment_confidence"),
    ):
        if model is None:
            continue
        try:
            result[label_key], result[confidence_key] = _predict_with_confidence(model, text)
            if task == "sentiment":
                result[label_key] = result[label_key].lower()
        except Exception as exc:
            logger.warning("%s prediction failed (%s)", task.capitalize(), type(exc).__name__)
    return result
