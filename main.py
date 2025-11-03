"""
Main application entry point for Dream Line Bot.
Configures dependency injection and starts the Flask application.
"""
import threading
from datetime import timedelta
from flask import Flask

from config import config
from src.utils import setup_logger
from src.core import container, MessageProcessor
from src.services import DatabaseService, AgentsAPIService, LineService
from src.services.user_handover_service import UserHandoverService
from src.services.google_sheets_service import GoogleSheetsService
from src.services.sync_scheduler import SyncScheduler
from src.controllers import WebhookController
from src.controllers.admin_controller import AdminController


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    # Configure Flask session
    app.secret_key = config.flask_secret_key
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    # Trust proxy headers (for ngrok/nginx)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Setup logging
    logger = setup_logger(__name__)
    logger.info(f"Starting Dream Line Bot in {config.environment} mode")

    # Create main Blueprint with /flask prefix (for NGINX routing)
    from flask import Blueprint
    flask_bp = Blueprint('flask', __name__, url_prefix='/flask')

    # Configure dependency injection
    setup_dependencies()

    # Initialize database
    db_service = container.resolve(DatabaseService)
    db_service.initialize_tables()

    # Initialize MessageProcessor
    message_processor = container.resolve(MessageProcessor)
    logger.info("Message processor initialized")
    line_service = container.resolve(LineService)
    webhook_controller = WebhookController(flask_bp, message_processor, line_service)

    # Initialize Admin Controller
    admin_controller = AdminController(flask_bp, db_service)
    logger.info("Admin controller initialized")

    # Register Blueprint to app
    app.register_blueprint(flask_bp)
    logger.info("Registered Flask Blueprint with /flask prefix")

    # Start background cleanup task for handover flags
    start_handover_cleanup_scheduler()

    # Start background sync to Google Sheets (if configured)
    start_sheets_sync_scheduler()

    logger.info("Dream Line Bot initialization completed with all services ready")
    return app


def setup_dependencies():
    """Configure dependency injection container."""

    # Register services as singletons (order matters for dependencies)
    container.register_singleton(DatabaseService)
    container.register_singleton(UserHandoverService)  # Must be before LineService
    container.register_singleton(LineService)

    # Register AgentsAPIService manually with LineService injection
    db_service = container.resolve(DatabaseService)
    line_service = container.resolve(LineService)
    agents_api_service = AgentsAPIService(db_service, line_service)
    container.register_instance(AgentsAPIService, agents_api_service)

    container.register_singleton(GoogleSheetsService)
    container.register_singleton(SyncScheduler)
    container.register_singleton(MessageProcessor)


def start_handover_cleanup_scheduler():
    """Start background scheduler for cleaning up expired handover flags."""
    cleanup_logger = setup_logger('handover_cleanup')
    
    def cleanup_job():
        try:
            handover_service = container.resolve(UserHandoverService)
            count = handover_service.cleanup_expired_flags()
            if count > 0:
                cleanup_logger.info(f"Cleaned up {count} expired handover flags")
        except Exception as e:
            cleanup_logger.error(f"Failed to cleanup expired handover flags: {e}")
        
        # Schedule next cleanup
        cleanup_interval = config.handover.cleanup_interval_minutes * 60  # Convert to seconds
        threading.Timer(cleanup_interval, cleanup_job).start()
    
    # Start the first cleanup job with delay to avoid infinite recursion
    cleanup_interval = config.handover.cleanup_interval_minutes * 60  # Convert to seconds
    threading.Timer(cleanup_interval, cleanup_job).start()
    cleanup_logger.info(f"Started handover flag cleanup scheduler (interval: {config.handover.cleanup_interval_minutes} minutes)")


def start_sheets_sync_scheduler():
    """Start background scheduler for syncing data to Google Sheets."""
    sync_logger = setup_logger('sheets_sync')

    def sync_job():
        try:
            # Check if Google Sheets sync is enabled
            if not config.google_sheets.enabled:
                sync_logger.debug("Google Sheets sync is disabled")
                return

            sync_scheduler = container.resolve(SyncScheduler)

            # Setup sync tracking table if needed
            sync_scheduler.setup_sync_tracking_table()

            # Perform sync for both message history and organization data
            success = sync_scheduler.sync_all_data()

            if success:
                sync_logger.info("Data sync completed successfully")
            else:
                sync_logger.warning("Data sync failed")

        except Exception as e:
            sync_logger.error(f"Failed to sync data to Google Sheets: {e}")

        # Schedule next sync
        sync_interval = config.google_sheets.sync_interval_minutes * 60  # Convert to seconds
        threading.Timer(sync_interval, sync_job).start()

    # Start the first sync job with delay to avoid infinite recursion
    sync_interval = config.google_sheets.sync_interval_minutes * 60  # Convert to seconds
    threading.Timer(sync_interval, sync_job).start()
    sync_logger.info(f"Started Google Sheets sync scheduler (interval: {config.google_sheets.sync_interval_minutes} minutes)")


# Create app instance for Gunicorn (production WSGI server)
app = create_app()

if __name__ == "__main__":
    # Use the already created app instance for development
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug,
        use_reloader=False  # Disable auto-reload to prevent double initialization
    )