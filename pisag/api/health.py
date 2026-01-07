"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from pisag.services.system_status import SystemStatus
from pisag.utils.database import get_request_session

health_blueprint = Blueprint("health", __name__, url_prefix="/health")


def _check_db() -> bool:
    try:
        session = get_request_session()
        session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_config_loaded() -> bool:
    return current_app.config.get("PISAG_CONFIG") is not None


def _build_payload(status: str, checks: dict, queue_size: int) -> dict:
    return {
        "status": status,
        "checks": checks,
        "uptime_seconds": SystemStatus.get_uptime(),
        "queue_size": queue_size,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@health_blueprint.route("/", methods=["GET"])
def health():
    db_ok = _check_db()
    hackrf_ok = SystemStatus.get_hackrf_status()
    cfg_ok = _check_config_loaded()
    queue = current_app.config.get("TRANSMISSION_QUEUE")
    queue_size = queue.size() if queue else 0

    checks = {"database": db_ok, "hackrf": hackrf_ok, "config": cfg_ok}

    if not db_ok:
        status = "unhealthy"
        code = 503
    elif not hackrf_ok:
        status = "degraded"
        code = 200
    else:
        status = "healthy"
        code = 200

    payload = _build_payload(status, checks, queue_size)
    return jsonify(payload), code


@health_blueprint.route("/ready", methods=["GET"])
def ready():
    db_ok = _check_db()
    hackrf_ok = SystemStatus.get_hackrf_status()
    cfg_ok = _check_config_loaded()
    ready_state = db_ok and hackrf_ok and cfg_ok
    code = 200 if ready_state else 503
    queue = current_app.config.get("TRANSMISSION_QUEUE")
    queue_size = queue.size() if queue else 0
    checks = {"database": db_ok, "hackrf": hackrf_ok, "config": cfg_ok}
    payload = _build_payload("ready" if ready_state else "not_ready", checks, queue_size)
    return jsonify(payload), code
