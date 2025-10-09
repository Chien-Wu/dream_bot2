"""
Main application entry point for Dream Line Bot.
Configures dependency injection and starts the Flask application.
"""
import threading
from flask import Flask

from config import config
from src.utils import setup_logger
from src.core import container, MessageProcessor
from src.services import DatabaseService, AgentsAPIService, LineService
from src.services.user_handover_service import UserHandoverService
from src.services.google_sheets_service import GoogleSheetsService
from src.services.sync_scheduler import SyncScheduler
from src.controllers import WebhookController


def create_app() -> Flask:
    """
    Create and configure the Flask application.
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Setup logging
    logger = setup_logger(__name__)
    logger.info(f"Starting Dream Line Bot in {config.environment} mode")
    
    # Configure dependency injection
    setup_dependencies()
    
    # Initialize database
    db_service = container.resolve(DatabaseService)
    db_service.initialize_tables()
    
    # Initialize MessageProcessor
    message_processor = container.resolve(MessageProcessor)
    logger.info("Message processor initialized")
    line_service = container.resolve(LineService)
    webhook_controller = WebhookController(app, message_processor, line_service)
    
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
    container.register_singleton(AgentsAPIService)
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