"""Core components for Dream Line Bot."""
from .container import container, Container
from .message_processor import MessageProcessor

__all__ = ['container', 'Container', 'MessageProcessor']