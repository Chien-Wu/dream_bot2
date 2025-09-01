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
from src.services.organization_analyzer import OrganizationDataAnalyzer
from src.services.welcome_flow_manager import WelcomeFlowManager
from src.services.admin_command_service import AdminCommandService
from src.services.user_handover_service import UserHandoverService
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
    
    # Eager initialization of critical services to ensure they're ready immediately
    # Initialize in dependency order to ensure proper singleton sharing
    admin_command_service = container.resolve(AdminCommandService)
    logger.info("Admin command service initialized and ready")
    
    # Pre-resolve MessageProcessor to ensure it uses the same AdminCommandService instance
    message_processor = container.resolve(MessageProcessor)
    logger.info("Message processor initialized with admin command service")
    line_service = container.resolve(LineService)
    welcome_flow_manager = container.resolve(WelcomeFlowManager)
    webhook_controller = WebhookController(app, message_processor, line_service, welcome_flow_manager)
    
    # Start background cleanup task for handover flags
    start_handover_cleanup_scheduler()
    
    logger.info("Dream Line Bot initialization completed with all services ready")
    return app


def setup_dependencies():
    """Configure dependency injection container."""
    
    # Register services as singletons (order matters for dependencies)
    container.register_singleton(DatabaseService)
    container.register_singleton(UserHandoverService)  # Must be before LineService
    container.register_singleton(LineService)
    container.register_singleton(AgentsAPIService)
    container.register_singleton(OrganizationDataAnalyzer)
    container.register_singleton(WelcomeFlowManager)
    container.register_singleton(AdminCommandService)
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
    
    # Start the first cleanup job
    cleanup_job()
    cleanup_logger.info(f"Started handover flag cleanup scheduler (interval: {config.handover.cleanup_interval_minutes} minutes)")


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug,
        use_reloader=False  # Disable auto-reload to prevent double initialization
    )