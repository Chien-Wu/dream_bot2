"""
Sync Scheduler Service for managing periodic data synchronization.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from src.services.database_service import DatabaseService
from src.services.google_sheets_service import GoogleSheetsService
from src.utils import setup_logger


logger = setup_logger(__name__)


class SyncScheduler:
    """Service for managing periodic data synchronization to external services."""

    def __init__(self, database_service: DatabaseService, sheets_service: GoogleSheetsService):
        self.db = database_service
        self.sheets = sheets_service
        self.last_sync_time = None

    def sync_message_history(self) -> bool:
        """
        Sync new message history records to Google Sheets.

        Returns:
            True if sync was successful, False otherwise
        """
        try:
            logger.info("Starting message history sync to Google Sheets")

            # Ensure sheet exists and is set up
            if not self.sheets.setup_message_history_sheet():
                logger.error("Failed to setup message history sheet")
                return False

            # Get last sync time from database
            last_sync = self._get_last_sync_time("message_history")

            # Get new messages since last sync
            new_messages = self._get_new_messages_since(last_sync)

            if not new_messages:
                logger.info("No new messages to sync")
                return True

            # Enrich messages with user data
            enriched_messages = self._enrich_messages_with_user_data(new_messages)

            # Sync to Google Sheets
            success = self.sheets.sync_message_history(enriched_messages)

            if success:
                # Update last sync time to the latest message timestamp
                latest_message_time = max(msg.get('created_at') for msg in new_messages)
                self._update_last_sync_time("message_history", latest_message_time)
                logger.info(f"Successfully synced {len(enriched_messages)} messages to Google Sheets (latest: {latest_message_time})")
            else:
                logger.error(f"Failed to sync {len(new_messages)} messages to Google Sheets")

            return success

        except Exception as e:
            logger.error(f"Error during message history sync: {e}")
            return False

    def sync_organization_data(self) -> bool:
        """
        Sync new organization data records to Google Sheets.

        Returns:
            True if sync was successful, False otherwise
        """
        try:
            logger.info("Starting organization data sync to Google Sheets")

            # Ensure sheet exists and is set up
            if not self.sheets.setup_organization_data_sheet():
                logger.error("Failed to setup organization data sheet")
                return False

            # Get last sync time from database
            last_sync = self._get_last_sync_time("organization_data")

            # Get new/updated organizations since last sync
            updated_organizations = self._get_updated_organizations_since(last_sync)

            if not updated_organizations:
                logger.info("No organization data to sync")
                return True

            # Deduplicate by user_id (keep latest record per user)
            deduplicated_orgs = self._deduplicate_organizations(updated_organizations)

            if len(deduplicated_orgs) < len(updated_organizations):
                logger.info(f"Deduplicated {len(updated_organizations)} records to {len(deduplicated_orgs)}")

            # Sync to Google Sheets
            success = self.sheets.sync_organization_data(deduplicated_orgs)

            if success:
                # Update last sync time to the latest organization timestamp
                latest_org_time = max(org.get('updated_at') for org in updated_organizations)
                self._update_last_sync_time("organization_data", latest_org_time)
                logger.info(f"Successfully synced {len(deduplicated_orgs)} organizations to Google Sheets (latest: {latest_org_time})")
            else:
                logger.error(f"Failed to sync {len(updated_organizations)} organizations to Google Sheets")

            return success

        except Exception as e:
            logger.error(f"Error during organization data sync: {e}")
            return False

    def sync_all_data(self) -> bool:
        """
        Sync both message history and organization data to Google Sheets.

        Returns:
            True if both syncs were successful, False otherwise
        """
        try:
            logger.info("Starting full data sync to Google Sheets")

            # Sync message history
            message_success = self.sync_message_history()

            # Sync organization data
            org_success = self.sync_organization_data()

            success = message_success and org_success

            if success:
                logger.info("Full data sync completed successfully")
            else:
                logger.warning("Full data sync completed with some failures")

            return success

        except Exception as e:
            logger.error(f"Error during full data sync: {e}")
            return False

    def _get_last_sync_time(self, sync_type: str = "message_history") -> Optional[datetime]:
        """Get the last sync timestamp from database."""
        try:
            # Query sync tracking table
            result = self.db.execute_query(
                "SELECT last_sync_time FROM sync_tracking WHERE sync_type = %s",
                params=(sync_type,),
                fetch_one=True
            )

            if result and result['last_sync_time']:
                return result['last_sync_time']
            else:
                # If no previous sync, start from 24 hours ago (UTC)
                return datetime.now(timezone.utc) - timedelta(hours=24)

        except Exception as e:
            logger.error(f"Failed to get last sync time: {e}")
            # Fallback to last hour (UTC)
            return datetime.now(timezone.utc) - timedelta(hours=1)

    def _get_new_messages_since(self, since_time: datetime) -> List[Dict[str, Any]]:
        """Get new message history records since the given time."""
        try:
            query = """
                SELECT
                    id,
                    user_id,
                    content,
                    message_type,
                    ai_response,
                    ai_explanation,
                    confidence,
                    created_at
                FROM message_history
                WHERE created_at >= %s
                ORDER BY created_at ASC
                LIMIT 1000
            """

            messages = self.db.execute_query(
                query,
                params=(since_time,),
                fetch_all=True
            )

            return messages or []

        except Exception as e:
            logger.error(f"Failed to get new messages: {e}")
            return []

    def _get_updated_organizations_since(self, since_time: datetime) -> List[Dict[str, Any]]:
        """Get organization records that have meaningful updates since the given time."""
        try:
            query = """
                SELECT
                    user_id,
                    organization_name,
                    reminded_count,
                    is_new,
                    created_at,
                    updated_at
                FROM organization_data
                WHERE (
                    updated_at >= %s
                    AND (
                        organization_name IS NOT NULL
                        OR reminded_count > 0
                        OR created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                    )
                )
                ORDER BY updated_at ASC
                LIMIT 1000
            """

            organizations = self.db.execute_query(
                query,
                params=(since_time,),
                fetch_all=True
            )

            return organizations or []

        except Exception as e:
            logger.error(f"Failed to get updated organizations: {e}")
            return []

    def _deduplicate_organizations(self, organizations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate organization records, keeping the latest record per user_id."""
        if not organizations:
            return []

        # Group by user_id and keep the record with latest updated_at
        user_records = {}
        for org in organizations:
            user_id = org.get('user_id')
            if user_id:
                if user_id not in user_records or org.get('updated_at', '') > user_records[user_id].get('updated_at', ''):
                    user_records[user_id] = org

        # Return deduplicated list sorted by updated_at
        deduplicated = list(user_records.values())
        deduplicated.sort(key=lambda x: x.get('updated_at', ''))
        return deduplicated

    def _enrich_messages_with_user_data(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich messages with user organization data."""
        try:
            enriched = []

            for msg in messages:
                user_id = msg.get('user_id')

                # Get user organization data
                org_data = self.db.get_organization_record(user_id)

                # Add organization data to message
                enriched_msg = msg.copy()
                if org_data:
                    enriched_msg['organization_name'] = org_data.get('organization_name', '')
                else:
                    enriched_msg['organization_name'] = ''

                enriched.append(enriched_msg)

            return enriched

        except Exception as e:
            logger.error(f"Failed to enrich messages with user data: {e}")
            return messages

    def _update_last_sync_time(self, sync_type: str, new_sync_time: datetime) -> None:
        """Update the last sync time in database using the actual last record timestamp."""
        try:
            current_time = datetime.now(timezone.utc)

            self.db.execute_query("""
                INSERT INTO sync_tracking (sync_type, last_sync_time, updated_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                last_sync_time = VALUES(last_sync_time),
                updated_at = VALUES(updated_at)
            """, params=(sync_type, new_sync_time, current_time))

            self.last_sync_time = new_sync_time
            logger.debug(f"Updated last sync time for {sync_type} to {new_sync_time}")

        except Exception as e:
            logger.error(f"Failed to update last sync time for {sync_type}: {e}")

    def setup_sync_tracking_table(self) -> bool:
        """Set up the sync tracking table if it doesn't exist."""
        try:
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS sync_tracking (
                    sync_type VARCHAR(50) PRIMARY KEY,
                    last_sync_time TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_sync_type (sync_type),
                    INDEX idx_last_sync_time (last_sync_time)
                )
            """

            self.db.execute_query(create_table_sql)
            logger.info("Sync tracking table setup completed")
            return True

        except Exception as e:
            logger.error(f"Failed to setup sync tracking table: {e}")
            return False
