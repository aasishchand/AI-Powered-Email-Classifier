"""Model service for stateless email inference."""

from __future__ import annotations

import logging
import os
from typing import Any

import joblib

from project.utils.config import config

logger = logging.getLogger(__name__)

_model: Any | None = None
_vectorizer: Any | None = None
_load_error: Exception | None = None


def _load_artifacts() -> None:
    """Load trained model and vectorizer once at import time."""
    global _model, _vectorizer, _load_error
    try:
        if not os.path.exists(config.MODEL_PATH):
            raise FileNotFoundError(f"Model file not found: {config.MODEL_PATH}")
        if not os.path.exists(config.VECTORIZER_PATH):
            raise FileNotFoundError(f"Vectorizer file not found: {config.VECTORIZER_PATH}")

        _model = joblib.load(config.MODEL_PATH)
        _vectorizer = joblib.load(config.VECTORIZER_PATH)
        logger.info("Model artifacts loaded successfully.")
    except Exception as exc:
        _load_error = exc
        logger.exception("Failed to load model artifacts.")


_load_artifacts()


def predict_email(text: str) -> tuple[str, float]:
    """
    Returns (predicted_label, confidence_score) for input email text.
    confidence_score is the max class probability from predict_proba().
    """
    if _load_error is not None:
        raise RuntimeError(f"Model artifacts unavailable: {_load_error}") from _load_error
    if _model is None or _vectorizer is None:
        raise RuntimeError("Model service is not initialized.")
    if not text or not text.strip():
        raise ValueError("Input text must be a non-empty string.")

    # 1) Vectorize incoming text into TF-IDF features
    text_features = _vectorizer.transform([text])
    # 2) Run model prediction to get class label
    predicted_label = str(_model.predict(text_features)[0])
    # 3) Use class probabilities for confidence score
    class_probs = _model.predict_proba(text_features)[0]
    confidence_score = float(max(class_probs))
    return predicted_label, confidence_score
