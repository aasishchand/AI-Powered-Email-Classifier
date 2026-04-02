"""Flask API for feedback updates and recent classified emails."""

from __future__ import annotations

import json
import logging
import time

from flask import Flask, Response, jsonify, request

from project.database import db
from project.utils.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.post("/feedback")
def post_feedback():
    """Update a classified email with human feedback."""
    try:
        app.logger.info("POST /feedback called")
        payload = request.get_json(silent=True) or {}
        email_id = payload.get("email_id")
        correct_label = payload.get("correct_label")

        if not email_id or not correct_label:
            return jsonify({"error": "email_id and correct_label are required"}), 400

        updated = db.update_feedback(str(email_id), str(correct_label))
        if not updated:
            return jsonify({"error": "email_id not found"}), 404
        return jsonify({"status": "updated", "email_id": str(email_id)}), 200
    except Exception:
        app.logger.exception("Feedback update failed")
        return jsonify({"error": "internal server error"}), 500


@app.get("/emails")
def get_emails():
    """Return the last N classified emails."""
    try:
        app.logger.info("GET /emails called")
        limit_raw = request.args.get("limit", "20")
        try:
            limit = int(limit_raw)
        except ValueError:
            limit = 20
        emails = db.get_recent_emails(limit=limit)
        return jsonify({"items": emails, "count": len(emails)}), 200
    except Exception:
        app.logger.exception("Failed to fetch recent emails")
        return jsonify({"error": "internal server error"}), 500


@app.get("/emails/stream")
def stream_emails():
    """Server-Sent Events: emit JSON when classified emails change (real-time clients)."""

    def event_stream():
        last_payload: str | None = None
        while True:
            try:
                emails = db.get_recent_emails(limit=100)
                payload = json.dumps({"items": emails, "count": len(emails)})
                if payload != last_payload:
                    last_payload = payload
                    yield f"data: {payload}\n\n"
                else:
                    yield ": keepalive\n\n"
            except Exception:
                logger.exception("SSE tick failed")
                yield 'data: {"error":"tick_failed"}\n\n'
            time.sleep(1.0)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def main() -> None:
    """Start Flask feedback API."""
    db.init_db()
    app.run(host="0.0.0.0", port=config.FEEDBACK_API_PORT, debug=False, threaded=True)


if __name__ == "__main__":
    main()
