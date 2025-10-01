"""
Google Sheets Service for syncing message history data.
"""
from typing import List, Dict, Any
from datetime import datetime

from src.utils import setup_logger
from config import config

# Try to import Google APIs, handle if not installed
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False


logger = setup_logger(__name__)


class GoogleSheetsService:
    """Service for syncing data to Google Sheets."""

    def __init__(self):
        """Initialize Google Sheets service using config settings."""
        self.service = None

        if not GOOGLE_APIS_AVAILABLE:
            logger.warning("Google APIs not available. Install with: pip install google-api-python-client google-auth")
            return

        if not config.google_sheets.enabled:
            logger.info("Google Sheets sync is disabled")
            return

        try:
            # Load credentials from config
            credentials = service_account.Credentials.from_service_account_file(
                config.google_sheets.credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )

            # Build the service
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
            self.service = None

    def is_connected(self) -> bool:
        """Check if service is properly connected."""
        return self.service is not None

    def setup_message_history_sheet(self, sheet_name: str = "MessageHistory") -> bool:
        """
        Set up the message history sheet with proper headers.

        Args:
            sheet_name: Name of the sheet to create/update

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Google Sheets service not connected")
            return False

        try:
            # Define headers for message history
            headers = [
                'Timestamp',
                'User ID',
                'Organization',
                'Message Type',
                'User Message',
                'AI Response',
                'AI Explanation',
                'Confidence',
                'Created At'
            ]

            # Check if sheet exists, create if not
            self._ensure_sheet_exists(sheet_name)

            # Update headers
            range_name = f"{sheet_name}!A1:I1"
            values = [headers]

            body = {
                'values': values
            }

            result = self.service.spreadsheets().values().update(
                spreadsheetId=config.google_sheets.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()

            logger.info(f"Message history sheet '{sheet_name}' setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup message history sheet: {e}")
            return False

    def setup_organization_data_sheet(self, sheet_name: str = "OrganizationData") -> bool:
        """
        Set up the organization data sheet with proper headers.

        Args:
            sheet_name: Name of the sheet to create/update

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Google Sheets service not connected")
            return False

        try:
            # Define headers for organization data
            headers = [
                'User ID',
                'Organization Name',
                'Reminded Count',
                'Is New User',
                'Created At',
                'Updated At'
            ]

            # Check if sheet exists, create if not
            self._ensure_sheet_exists(sheet_name)

            # Update headers
            range_name = f"{sheet_name}!A1:F1"
            values = [headers]

            body = {
                'values': values
            }

            result = self.service.spreadsheets().values().update(
                spreadsheetId=config.google_sheets.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()

            logger.info(f"Organization data sheet '{sheet_name}' setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup organization data sheet: {e}")
            return False

    def sync_message_history(self, messages: List[Dict[str, Any]], sheet_name: str = "MessageHistory") -> bool:
        """
        Sync message history data to Google Sheets.

        Args:
            messages: List of message dictionaries to sync
            sheet_name: Name of the sheet to sync to

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Google Sheets service not connected")
            return False

        if not messages:
            logger.debug("No messages to sync")
            return True

        try:
            # Convert messages to sheet format
            rows = []
            for msg in messages:
                # Handle confidence field - convert Decimal to float or empty string
                confidence = msg.get('confidence', '')
                if confidence is not None and confidence != '':
                    try:
                        # Convert Decimal/float to float, then to string for Google Sheets
                        confidence = str(float(confidence))
                    except (ValueError, TypeError, AttributeError):
                        confidence = ''
                else:
                    confidence = ''

                row = [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Timestamp
                    str(msg.get('user_id', '')),                   # User ID
                    str(msg.get('organization_name', '')),         # Organization
                    str(msg.get('message_type', 'text')),          # Message Type
                    str(msg.get('content', '')),                   # User Message
                    str(msg.get('ai_response', '')),               # AI Response
                    str(msg.get('ai_explanation', '')),            # AI Explanation
                    confidence,                                    # Confidence as string
                    str(msg.get('created_at', ''))                 # Created At
                ]
                rows.append(row)

            # Append to sheet
            range_name = f"{sheet_name}!A:I"

            # Ensure all values are JSON serializable (strings, numbers, booleans)
            sanitized_rows = []
            for row in rows:
                sanitized_row = []
                for value in row:
                    if value is None:
                        sanitized_row.append('')
                    elif isinstance(value, (str, int, float, bool)):
                        sanitized_row.append(value)
                    else:
                        # Convert any other type to string
                        sanitized_row.append(str(value))
                sanitized_rows.append(sanitized_row)

            body = {
                'values': sanitized_rows
            }

            result = self.service.spreadsheets().values().append(
                spreadsheetId=config.google_sheets.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            logger.info(f"Successfully synced {len(messages)} messages to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync messages to Google Sheets: {e}")
            return False

    def sync_organization_data(self, organizations: List[Dict[str, Any]], sheet_name: str = "OrganizationData") -> bool:
        """
        Sync organization data to Google Sheets.

        Args:
            organizations: List of organization dictionaries to sync
            sheet_name: Name of the sheet to sync to

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.error("Google Sheets service not connected")
            return False

        if not organizations:
            logger.debug("No organizations to sync")
            return True

        try:
            # Convert organizations to sheet format
            rows = []
            for org in organizations:
                is_new_user = org.get('is_new', False)
                row = [
                    str(org.get('user_id', '')),                    # User ID
                    str(org.get('organization_name', '')),          # Organization Name
                    int(org.get('reminded_count', 0)),              # Reminded Count
                    'Yes' if is_new_user else 'No',                # Is New User (human readable)
                    str(org.get('created_at', '')),                 # Created At
                    str(org.get('updated_at', ''))                  # Updated At
                ]
                rows.append(row)

            # Append to sheet
            range_name = f"{sheet_name}!A:F"

            # Ensure all values are JSON serializable (strings, numbers, booleans)
            sanitized_rows = []
            for row in rows:
                sanitized_row = []
                for value in row:
                    if value is None:
                        sanitized_row.append('')
                    elif isinstance(value, (str, int, float, bool)):
                        sanitized_row.append(value)
                    else:
                        # Convert any other type to string
                        sanitized_row.append(str(value))
                sanitized_rows.append(sanitized_row)

            body = {
                'values': sanitized_rows
            }

            result = self.service.spreadsheets().values().append(
                spreadsheetId=config.google_sheets.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            logger.info(f"Successfully synced {len(organizations)} organizations to Google Sheets")
            return True

        except Exception as e:
            logger.error(f"Failed to sync organizations to Google Sheets: {e}")
            return False

    def _ensure_sheet_exists(self, sheet_name: str) -> bool:
        """Ensure a sheet with the given name exists."""
        try:
            # Get existing sheets
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=config.google_sheets.spreadsheet_id
            ).execute()

            existing_sheets = [sheet['properties']['title'] for sheet in sheet_metadata['sheets']]

            if sheet_name not in existing_sheets:
                # Create the sheet
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]

                body = {
                    'requests': requests
                }

                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=config.google_sheets.spreadsheet_id,
                    body=body
                ).execute()

                logger.info(f"Created new sheet: {sheet_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to ensure sheet exists: {e}")
            return False
