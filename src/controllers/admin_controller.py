"""
Admin controller for dashboard and user management.
"""
from datetime import timedelta
from flask import Blueprint, session, redirect, url_for, request, jsonify, render_template
from authlib.integrations.flask_client import OAuth

from config import config
from src.utils import setup_logger, require_admin_auth
from src.services import DatabaseService
from src.services.user_handover_service import UserHandoverService
from src.core import container


logger = setup_logger(__name__)


class AdminController:
    """Controller for admin dashboard and API endpoints."""

    def __init__(self, blueprint: Blueprint, database_service: DatabaseService):
        self.blueprint = blueprint
        self.db = database_service
        self.handover_service = container.resolve(UserHandoverService)

        # Initialize OAuth - need to get the parent Flask app from blueprint
        # OAuth must be initialized with the Flask app, not the Blueprint
        from flask import current_app
        self.oauth = OAuth()

        # Register OAuth after blueprint is registered to app
        # We'll do this in a before_first_request handler
        @self.blueprint.before_app_request
        def init_oauth():
            if not hasattr(self, 'google'):
                self.oauth.init_app(current_app)
                self.google = self.oauth.register(
                    name='google',
                    client_id=config.google_oauth.client_id,
                    client_secret=config.google_oauth.client_secret,
                    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                    client_kwargs={
                        'scope': 'openid email profile'
                    }
                )

        self._register_routes()

    def _register_routes(self):
        """Register all admin routes."""

        @self.blueprint.route('/admin')
        @require_admin_auth
        def admin_dashboard():
            """Main admin dashboard page."""
            return render_template('admin_dashboard.html',
                                   user_email=session.get('user_email'))

        @self.blueprint.route('/admin/login')
        def admin_login():
            """Admin login page."""
            # If already authenticated, redirect to dashboard
            if session.get('authenticated'):
                return redirect(url_for('flask.admin_dashboard'))

            return render_template('admin_login.html')

        @self.blueprint.route('/admin/auth/google')
        def admin_auth_google():
            """Initiate Google OAuth flow."""
            # Build callback URL
            redirect_uri = url_for('flask.admin_auth_callback', _external=True)
            logger.info(f"OAuth redirect URI: {redirect_uri}")
            return self.google.authorize_redirect(redirect_uri)

        @self.blueprint.route('/admin/auth/callback')
        def admin_auth_callback():
            """Handle Google OAuth callback."""
            try:
                # Exchange authorization code for token
                token = self.google.authorize_access_token()

                # Get user info from Google
                user_info = token.get('userinfo')
                if not user_info:
                    logger.error("Failed to get user info from Google token")
                    return "Authentication failed: Could not retrieve user information", 500

                user_email = user_info.get('email')
                user_name = user_info.get('name')

                logger.info(f"OAuth callback received for email: {user_email}")

                # Check if email is in allowed list
                if user_email not in config.google_oauth.allowed_emails:
                    logger.warning(f"Unauthorized login attempt by {user_email}")
                    return render_template('admin_login.html',
                                           error=f"Access Denied: {user_email} is not authorized"), 403

                # Create session
                session.permanent = True
                session['authenticated'] = True
                session['user_email'] = user_email
                session['user_name'] = user_name

                logger.info(f"Admin {user_email} logged in successfully")

                return redirect(url_for('flask.admin_dashboard'))

            except Exception as e:
                logger.error(f"OAuth callback error: {e}")
                return f"Authentication failed: {str(e)}", 500

        @self.blueprint.route('/admin/logout')
        def admin_logout():
            """Logout and clear session."""
            user_email = session.get('user_email', 'unknown')
            session.clear()
            logger.info(f"Admin {user_email} logged out")
            return redirect(url_for('flask.admin_login'))

        # API endpoints

        @self.blueprint.route('/admin/api/users')
        @require_admin_auth
        def api_get_users():
            """Get all users with handover status."""
            try:
                users = self.db.get_all_users_with_handover_status(limit=100)

                # Calculate stats
                total_count = len(users)
                active_count = sum(1 for u in users if not u['is_blocked'])
                blocked_count = sum(1 for u in users if u['is_blocked'])

                # Convert datetime objects to strings for JSON serialization
                for user in users:
                    if user.get('last_activity'):
                        user['last_activity'] = user['last_activity'].strftime('%Y-%m-%d %H:%M:%S')
                    if user.get('blocked_until'):
                        user['blocked_until'] = user['blocked_until'].strftime('%Y-%m-%d %H:%M:%S')

                return jsonify({
                    'success': True,
                    'users': users,
                    'stats': {
                        'total': total_count,
                        'active': active_count,
                        'blocked': blocked_count
                    }
                })

            except Exception as e:
                logger.error(f"Failed to get users: {e}")
                return jsonify({
                    'success': False,
                    'message': '獲取用戶列表失敗',
                    'error': str(e)
                }), 500

        @self.blueprint.route('/admin/api/user/<user_id>/block', methods=['POST'])
        @require_admin_auth
        def api_block_user(user_id):
            """Block AI responses for specific user."""
            try:
                # Set handover flag (blocks AI for 1 hour)
                self.handover_service.set_handover_flag(user_id)

                admin_email = session.get('user_email', 'unknown')
                logger.info(f"Admin {admin_email} blocked user {user_id}")

                return jsonify({
                    'success': True,
                    'message': 'AI已停用',
                    'user_id': user_id,
                    'is_blocked': True
                })

            except Exception as e:
                logger.error(f"Failed to block user {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'message': '操作失敗',
                    'error': str(e)
                }), 500

        @self.blueprint.route('/admin/api/user/<user_id>/unblock', methods=['POST'])
        @require_admin_auth
        def api_unblock_user(user_id):
            """Unblock AI responses for specific user."""
            try:
                # Clear handover flag
                self.handover_service.clear_handover_flag(user_id)

                admin_email = session.get('user_email', 'unknown')
                logger.info(f"Admin {admin_email} unblocked user {user_id}")

                return jsonify({
                    'success': True,
                    'message': 'AI已啟用',
                    'user_id': user_id,
                    'is_blocked': False
                })

            except Exception as e:
                logger.error(f"Failed to unblock user {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'message': '操作失敗',
                    'error': str(e)
                }), 500
