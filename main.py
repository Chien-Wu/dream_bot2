"""
Main application entry point for Dream Line Bot.
Configures dependency injection and starts the Flask application.
"""
from flask import Flask

from config import config
from src.utils import setup_logger
from src.core import container, MessageProcessor
from src.services import DatabaseService, OpenAIService, LineService
from src.services.organization_analyzer import OrganizationDataAnalyzer
from src.services.welcome_flow_manager import WelcomeFlowManager
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
    
    # Setup webhook controller
    message_processor = container.resolve(MessageProcessor)
    line_service = container.resolve(LineService)
    welcome_flow_manager = container.resolve(WelcomeFlowManager)
    webhook_controller = WebhookController(app, message_processor, line_service, welcome_flow_manager)
    
    logger.info("Dream Line Bot initialization completed")
    return app


def setup_dependencies():
    """Configure dependency injection container."""
    
    # Register services as singletons
    container.register_singleton(DatabaseService)
    container.register_singleton(LineService)
    container.register_singleton(OpenAIService)
    container.register_singleton(OrganizationDataAnalyzer)
    container.register_singleton(WelcomeFlowManager)
    container.register_singleton(MessageProcessor)


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug
    )