"""
Webhook controller for handling LINE Bot webhooks.
"""
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, FollowEvent

from config import config
from src.utils import setup_logger, log_user_action
from src.core import MessageProcessor
from src.services import LineService


logger = setup_logger(__name__)


class WebhookController:
    """Controller for LINE webhook events."""
    
    def __init__(self,
                 app: Flask,
                 message_processor: MessageProcessor,
                 line_service: LineService):
        self.app = app
        self.processor = message_processor
        self.line = line_service
        self.handler = WebhookHandler(config.line.channel_secret)
        
        self._register_routes()
        self._register_handlers()
    
    def _register_routes(self):
        """Register Flask routes."""
        
        @self.app.route("/callback", methods=['POST'])
        def callback():
            signature = request.headers.get('X-Line-Signature', '')
            body = request.get_data(as_text=True)
            
            try:
                self.handler.handle(body, signature)
            except Exception as e:
                logger.error(f"LINE Webhook Error: {e}")
                abort(400)
                
            return 'OK'
        
        @self.app.route("/health", methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return {'status': 'healthy', 'service': 'dream-line-bot'}, 200
    
    def _register_handlers(self):
        """Register LINE event handlers."""
        
        @self.handler.add(MessageEvent)
        def handle_message(event):
            """Handle incoming messages."""
            try:
                message = self.line.extract_message(event)
                if message:
                    self.processor.process_message(message)
                    
            except Exception as e:
                logger.error(f"Error handling message event: {e}")
        
        @self.handler.add(FollowEvent)
        def handle_follow(event):
            """Handle new user follow events."""
            try:
                user_id = event.source.user_id

                log_user_action(logger, user_id, "user_followed")

                # User record will be created automatically when they send their first message
                # No special onboarding flow needed

            except Exception as e:
                logger.error(f"Error handling follow event: {e}")