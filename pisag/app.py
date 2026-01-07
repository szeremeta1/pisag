"""Flask application factory for PISAG."""

from __future__ import annotations

import atexit
import logging
import os
import signal
from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO

from pisag.config import get_config
from pisag.utils.database import init_app_db
from pisag.utils.logging import get_logger
from pisag.api.routes import api_blueprint
from pisag.api.socketio import register_socketio
from pisag.api.health import health_blueprint
from pisag.services.transmission_queue import TransmissionQueue
from pisag.services.transmission_worker import TransmissionWorker
from pisag.services.device_monitor import DeviceMonitor
from pisag.services.system_status import SystemStatus

_BASE_PATH = Path(__file__).resolve().parent.parent
_STATIC_PATH = _BASE_PATH / "static"
_socketio = SocketIO(cors_allowed_origins="*")
_shutdown_initiated = False


def create_app(config_path: str = "config.json") -> Flask:
    """
    Create and configure Flask application.

    Args:
        config_path: Path to configuration file

    Returns:
        Configured Flask application instance
    """
    cfg = get_config(config_path)
    app = Flask(
        __name__,
        static_folder=str(_STATIC_PATH),
        static_url_path="/static",
    )

    app.config["SECRET_KEY"] = cfg.get("web", {}).get("secret_key") or os.getenv("PISAG_SECRET_KEY") or os.urandom(24)
    app.config["JSON_SORT_KEYS"] = True
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
    app.config["PISAG_CONFIG"] = cfg

    CORS(app, resources={r"*": {"origins": "*"}})

    logger = get_logger(__name__)
    level_name = str(cfg.get("system", {}).get("log_level", "INFO")).upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.info("PISAG Flask application starting")

    _socketio.init_app(
        app,
        cors_allowed_origins="*",
        ping_timeout=20,
        ping_interval=25,
        logger=app.debug,
        engineio_logger=app.debug,
    )

    app.register_blueprint(api_blueprint)
    app.register_blueprint(health_blueprint)
    register_socketio(_socketio)
    init_app_db(app)

    queue = TransmissionQueue()
    worker = TransmissionWorker(queue, config_path)
    try:
        worker.start()
    except Exception:
        logger.warning("Transmission worker started without SDR connection", exc_info=True)
    app.config["TRANSMISSION_QUEUE"] = queue
    app.config["TRANSMISSION_WORKER"] = worker

    monitor = DeviceMonitor(worker.sdr, queue, config_provider=lambda: app.config.get("PISAG_CONFIG", {}))
    monitor.start()
    app.config["DEVICE_MONITOR"] = monitor

    def _json_error(message: str, status_code: int, details: dict | None = None):
        payload = {"error": message, "timestamp": datetime.now(timezone.utc).isoformat()}
        if details is not None:
            payload["details"] = details
        return jsonify(payload), status_code

    def _error_context():
        try:
            return {"method": request.method, "path": request.path, "remote_addr": request.remote_addr}
        except Exception:
            return {}

    @app.errorhandler(404)
    def handle_not_found(error):  # noqa: ANN001
        logger.warning("Not found", extra=_error_context())
        return _json_error("Not Found", 404)

    @app.route("/")
    def index():
        """Serve the main application page."""
        return send_file(str(_STATIC_PATH / "index.html"))

    @app.errorhandler(400)
    def handle_bad_request(error):  # noqa: ANN001
        logger.warning("Bad request", extra=_error_context())
        return _json_error("Bad Request", 400)

    @app.errorhandler(500)
    def handle_server_error(error):  # noqa: ANN001
        logger.exception("Unhandled server error", extra=_error_context())
        return _json_error("Internal Server Error", 500)

    @app.errorhandler(503)
    def handle_unavailable(error):  # noqa: ANN001
        logger.warning("Service unavailable", extra=_error_context())
        return _json_error("Service Unavailable", 503)

    def shutdown_handler(*_args):
        global _shutdown_initiated
        if _shutdown_initiated:
            return
        _shutdown_initiated = True
        logger.info("Shutdown initiated")
        try:
            worker.stop()
        except Exception:
            logger.error("Failed to stop worker", exc_info=True)
        monitor_instance = app.config.get("DEVICE_MONITOR")
        try:
            if monitor_instance:
                monitor_instance.stop()
        except Exception:
            logger.error("Failed to stop monitor", exc_info=True)
        try:
            _socketio.stop()  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            logging.shutdown()
        except Exception:
            pass
        logger.info("Shutdown complete")

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    atexit.register(shutdown_handler)

    return app


def main() -> None:
    app = create_app()
    cfg = app.config.get("PISAG_CONFIG", {})
    _socketio.run(
        app,
        host=cfg.get("web", {}).get("host", "0.0.0.0"),
        port=int(cfg.get("web", {}).get("port", 5000)),
        debug=bool(cfg.get("web", {}).get("debug", False)),
    )


if __name__ == "__main__":
    main()
