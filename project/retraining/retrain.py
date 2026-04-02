"""Adaptive retraining pipeline using human feedback data."""

from __future__ import annotations

import logging
from collections import Counter

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

from project.database import db
from project.utils.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def retrain() -> None:
    """Retrain model artifacts from feedback-labeled records."""
    db.init_db()
    feedback_rows = db.get_feedback_data()
    sample_count = len(feedback_rows)

    if sample_count < 5:
        logger.warning(
            "Not enough feedback samples to retrain. Required>=5, received=%d.",
            sample_count,
        )
        return

    corpus = [str(row["text"]) for row in feedback_rows]
    labels = [str(row["feedback"]) for row in feedback_rows]

    vectorizer = TfidfVectorizer()
    x_train = vectorizer.fit_transform(corpus)

    model = LogisticRegression(max_iter=1000)
    model.fit(x_train, labels)

    train_predictions = model.predict(x_train)
    train_accuracy = accuracy_score(labels, train_predictions)
    report = classification_report(labels, train_predictions)

    joblib.dump(model, config.MODEL_PATH)
    joblib.dump(vectorizer, config.VECTORIZER_PATH)

    logger.info("Retraining complete.")
    logger.info("Samples used: %d", sample_count)
    logger.info("Unique labels found: %s", dict(Counter(labels)))
    logger.info("Saved model to: %s", config.MODEL_PATH)
    logger.info("Saved vectorizer to: %s", config.VECTORIZER_PATH)
    logger.info("Training accuracy: %.4f", train_accuracy)
    logger.info("Classification report:\n%s", report)


if __name__ == "__main__":
    retrain()
