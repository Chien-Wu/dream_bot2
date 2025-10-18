"""
Authentication decorator for admin routes.
"""
from functools import wraps
from flask import session, redirect, url_for, request

from config import config
from src.utils import setup_logger


logger = setup_logger(__name__)


def require_admin_auth(f):
    """
    Decorator to require Google OAuth authentication for admin routes.

    Checks if user is authenticated and email is in allowed list.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if 'authenticated' not in session or not session['authenticated']:
            logger.warning(f"Unauthenticated access attempt to {request.path}")
            return redirect(url_for('admin_login'))

        # Check if email is in allowed list
        user_email = session.get('user_email')
        if not user_email or user_email not in config.google_oauth.allowed_emails:
            logger.warning(f"Unauthorized access attempt by {user_email} to {request.path}")
            return "Access Denied: You are not authorized to access this resource", 403

        return f(*args, **kwargs)

    return decorated_function
