"""REST API routes for PISAG."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_socketio import SocketIO
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import selectinload

from pisag.api.serializers import serialize_config, serialize_message, serialize_pager
from pisag.api.socketio import emit_message_queued, emit_status_update
from pisag.models import Message
from pisag.services.analytics_service import AnalyticsService
from pisag.services.config_service import ConfigService
from pisag.services.message_service import MessageService
from pisag.services.pager_service import PagerService
from pisag.services.system_status import SystemStatus
from pisag.utils.database import get_request_session
from pisag.utils.logging import get_logger

api_blueprint = Blueprint("api", __name__, url_prefix="/api")
_logger = get_logger(__name__)


# Helpers -----------------------------------------------------------------

def _get_queue():
    return current_app.config.get("TRANSMISSION_QUEUE")


def _get_worker_running():
    worker = current_app.config.get("TRANSMISSION_WORKER")
    return worker is not None and worker._running  # type: ignore[attr-defined]


def _get_socketio() -> SocketIO:
    return current_app.extensions.get("socketio")  # type: ignore[return-value]


def _error_response(message: str, status_code: int = 500, details: dict | None = None):
    payload = {
        "error": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code


def _request_context_extra():
    try:
        return {
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
        }
    except Exception:
        return {}


# Message endpoints -------------------------------------------------------


@api_blueprint.route("/send", methods=["POST"])
def send_message():
    payload = request.get_json(force=True, silent=True) or {}
    recipients = payload.get("recipients") or payload.get("ric") or []
    if isinstance(recipients, str):
        recipients = [recipients]
    message_text = payload.get("message") or payload.get("message_text") or ""
    message_type = payload.get("type") or payload.get("message_type") or "alphanumeric"

    cfg = current_app.config.get("PISAG_CONFIG", {})
    frequency = float(cfg.get("system", {}).get("frequency", 439.9875))
    baud_rate = int(cfg.get("pocsag", {}).get("baud_rate", 512))

    session = get_request_session()
    service = MessageService(_get_queue())
    try:
        message = service.send_message(session, recipients, message_text, message_type, frequency, baud_rate)
        emit_message_queued(message.id, len(recipients))
        return (
            jsonify({"status": "success", "message_id": message.id, "timestamp": datetime.utcnow().isoformat()}),
            201,
        )
    except ValueError as exc:
        session.rollback()
        _logger.warning("Send validation failed", extra={"error": str(exc), **_request_context_extra()})
        return _error_response(str(exc), 400)
    except OperationalError as exc:
        session.rollback()
        _logger.error("Database unavailable during send", exc_info=True, extra=_request_context_extra())
        return _error_response("Database unavailable", 503)
    except Exception as exc:  # pragma: no cover - safety
        session.rollback()
        _logger.error("Send failed", exc_info=True, extra=_request_context_extra())
        return _error_response("Internal server error", 500)


@api_blueprint.route("/messages", methods=["GET"])
def list_messages():
    try:
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", 50))
        if offset < 0 or limit < 0:
            raise ValueError("offset and limit must be non-negative")
    except ValueError as exc:
        return _error_response(str(exc), 400)

    session = get_request_session()
    try:
        messages = (
            session.query(Message)
            .options(selectinload(Message.recipients).selectinload("pager"))
            .order_by(Message.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return jsonify([serialize_message(m) for m in messages])
    except OperationalError:
        return _error_response("Database unavailable", 503)


@api_blueprint.route("/messages/<int:message_id>/resend", methods=["POST"])
def resend_message(message_id: int):
    session = get_request_session()
    service = MessageService(_get_queue())
    try:
        new_message = service.resend_message(session, message_id)
        emit_message_queued(new_message.id, len(new_message.recipients))
        return jsonify({"status": "success", "message_id": new_message.id}), 201
    except ValueError as exc:
        session.rollback()
        status = 404 if "not found" in str(exc).lower() else 400
        return _error_response(str(exc), status)
    except OperationalError:
        session.rollback()
        return _error_response("Database unavailable", 503)


# Pager endpoints ---------------------------------------------------------

@api_blueprint.route("/pagers", methods=["GET"])
def list_pagers():
    session = get_request_session()
    service = PagerService()
    try:
        pagers = service.get_all_pagers(session)
        return jsonify([serialize_pager(p) for p in pagers])
    except OperationalError:
        return _error_response("Database unavailable", 503)


@api_blueprint.route("/pagers", methods=["POST"])
def create_pager():
    payload = request.get_json(force=True, silent=True) or {}
    name = payload.get("name")
    ric_address = payload.get("ric_address")
    notes = payload.get("notes")
    session = get_request_session()
    service = PagerService()
    try:
        pager = service.create_pager(session, name, ric_address, notes)
        return jsonify(serialize_pager(pager)), 201
    except ValueError as exc:
        session.rollback()
        return _error_response(str(exc), 400)
    except IntegrityError:
        session.rollback()
        return _error_response("Pager already exists", 400)
    except OperationalError:
        session.rollback()
        return _error_response("Database unavailable", 503)


@api_blueprint.route("/pagers/<int:pager_id>", methods=["PUT"])
def update_pager(pager_id: int):
    payload = request.get_json(force=True, silent=True) or {}
    session = get_request_session()
    service = PagerService()
    try:
        pager = service.update_pager(session, pager_id, payload.get("name"), payload.get("ric_address"), payload.get("notes"))
        return jsonify(serialize_pager(pager))
    except ValueError as exc:
        session.rollback()
        status = 404 if "not found" in str(exc).lower() else 400
        return _error_response(str(exc), status)
    except IntegrityError:
        session.rollback()
        return _error_response("Pager already exists", 400)
    except OperationalError:
        session.rollback()
        return _error_response("Database unavailable", 503)


@api_blueprint.route("/pagers/<int:pager_id>", methods=["DELETE"])
def delete_pager(pager_id: int):
    session = get_request_session()
    service = PagerService()
    try:
        service.delete_pager(session, pager_id)
        return jsonify({"status": "success"})
    except ValueError as exc:
        session.rollback()
        status = 404 if "not found" in str(exc).lower() else 400
        return _error_response(str(exc), status)
    except OperationalError:
        session.rollback()
        return _error_response("Database unavailable", 503)


# Configuration endpoints -------------------------------------------------

@api_blueprint.route("/config", methods=["GET"])
def get_config_endpoint():
    cfg_service = ConfigService()
    try:
        return jsonify(serialize_config(cfg_service.get_configuration()))
    except OperationalError:
        return _error_response("Database unavailable", 503)


@api_blueprint.route("/config", methods=["PUT"])
def update_config_endpoint():
    payload = request.get_json(force=True, silent=True) or {}
    session = get_request_session()
    cfg_service = ConfigService()
    try:
        cfg = cfg_service.update_configuration(session, payload)
        current_app.config["PISAG_CONFIG"] = cfg

        worker = current_app.config.get("TRANSMISSION_WORKER")
        if worker:
            worker.config = cfg

        emit_status_update({"config": cfg})
        return jsonify(serialize_config(cfg))
    except ValueError as exc:
        session.rollback()
        return _error_response(str(exc), 400)
    except OperationalError:
        session.rollback()
        return _error_response("Database unavailable", 503)


# Analytics endpoint ------------------------------------------------------

@api_blueprint.route("/analytics", methods=["GET"])
def analytics():
    session = get_request_session()
    svc = AnalyticsService()
    try:
        stats = svc.get_statistics(session)
        time_series = svc.get_messages_over_time(session)
        freq_usage = svc.get_frequency_usage(session)
        pager_activity = svc.get_pager_activity(session)
        return jsonify(
            {
                "statistics": stats,
                "time_series": time_series,
                "frequency_usage": freq_usage,
                "pager_activity": pager_activity,
            }
        )
    except OperationalError:
        return _error_response("Database unavailable", 503)


# Status endpoint ---------------------------------------------------------

@api_blueprint.route("/status", methods=["GET"])
def status():
    cfg = current_app.config.get("PISAG_CONFIG", {})
    queue = _get_queue()
    worker_running = _get_worker_running()
    status_dict = SystemStatus.get_status_dict(queue.size() if queue else 0)
    status_dict["worker_running"] = worker_running
    status_dict["frequency"] = cfg.get("system", {}).get("frequency")
    status_dict["baud_rate"] = cfg.get("pocsag", {}).get("baud_rate")

    if not worker_running or not status_dict.get("hackrf_connected"):
        return _error_response("Service unavailable", 503, details=status_dict)

    return jsonify(status_dict)


# Error handlers ----------------------------------------------------------


@api_blueprint.errorhandler(404)
def _not_found(error):  # noqa: ANN001
    return _error_response("Not found", 404)


@api_blueprint.errorhandler(ValueError)
def _value_error(error):  # noqa: ANN001
    return _error_response(str(error), 400)


@api_blueprint.errorhandler(Exception)
def _generic_error(error):  # noqa: ANN001
    _logger.error("API error", exc_info=True, extra=_request_context_extra())
    return _error_response("Internal server error", 500)
