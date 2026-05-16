"""
AWS DynamoDB Cloud Identity Store — Serverless, KMS-Encrypted
==============================================================
Stores verified user identity records in AWS DynamoDB with the strongest
security controls available for real trading:

  - AES-256 encryption at rest via AWS KMS (Customer Managed Key)
  - Encryption in transit via TLS (all DynamoDB API calls)
  - Point-in-Time Recovery (PITR) protects against accidental data loss
  - TTL auto-expires unverified records after configurable period
  - IAM least-privilege policies enforce access control
  - On-demand capacity mode — serverless, scales to zero when idle

Identity records stored:
  - email (partition key)
  - provider (github / linkedin / dual)
  - provider_username
  - display_name (derived from GitHub + LinkedIn only, no custom aliases)
  - github_username, linkedin_username
  - github_display_name, linkedin_display_name
  - verified, verified_at, reputation_score
  - crypto_priority, crypto_estimated_years, crypto_can_trade, crypto_signals
  - dual_verified, providers
  - ttl (auto-expire for unverified records)

When DYNAMODB_ENABLED=False, the system falls back to the in-memory
_verification_db dict in identity_verification.py — suitable for
development and testing only.

Usage:
    from app.core.cloud_identity_store import cloud_store

    # Store a verified identity
    cloud_store.put_identity(email, record_dict)

    # Retrieve identity
    record = cloud_store.get_identity(email)

    # Delete identity
    cloud_store.delete_identity(email)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ─── DynamoDB Client (Lazy Singleton) ─────────────────────────────────────────

_dynamodb_resource = None
_table = None
_table_verified = False  # True after we confirmed table exists


def _get_dynamodb_resource():
    """Get or create boto3 DynamoDB resource (lazy singleton)."""
    global _dynamodb_resource
    if _dynamodb_resource is not None:
        return _dynamodb_resource

    settings = get_settings()

    # Build boto3 session — use IAM role if keys are empty
    session_kwargs: dict = {
        "region_name": settings.DYNAMODB_REGION,
    }
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        session_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        session_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

    try:
        import boto3
        _dynamodb_resource = boto3.resource("dynamodb", **session_kwargs)
        logger.info(
            "DynamoDB resource created in %s (explicit keys=%s)",
            settings.DYNAMODB_REGION,
            bool(settings.AWS_ACCESS_KEY_ID),
        )
    except ImportError:
        logger.warning("boto3 not installed — DynamoDB cloud identity store unavailable")
        return None
    except Exception as exc:
        logger.error("Failed to create DynamoDB resource: %s", exc)
        return None

    return _dynamodb_resource


def _get_table():
    """Get or create DynamoDB table reference (lazy singleton)."""
    global _table, _table_verified
    if _table is not None and _table_verified:
        return _table

    resource = _get_dynamodb_resource()
    if resource is None:
        return None

    settings = get_settings()
    table_name = settings.DYNAMODB_TABLE_NAME

    try:
        _table = resource.Table(table_name)
        # Verify table exists by describing it
        _table.load()
        _table_verified = True
        logger.info("DynamoDB table '%s' loaded (ARN: %s)", table_name, _table.table_arn)
        return _table
    except Exception as exc:
        # Table doesn't exist — try to create it
        logger.info("DynamoDB table '%s' not found, creating...", table_name)
        return _create_table(resource, table_name)


def _create_table(resource, table_name: str):
    """Create the DynamoDB identity table with KMS encryption and PITR."""
    global _table, _table_verified
    settings = get_settings()

    try:
        import boto3
    except ImportError:
        return None

    # Build SSE specification
    sse_spec = {"Enabled": True}  # Default: AWS-owned key
    if settings.DYNAMODB_KMS_KEY_ID:
        sse_spec = {
            "Enabled": True,
            "SSEType": "KMS",
            "KMSMasterKeyId": settings.DYNAMODB_KMS_KEY_ID,
        }

    try:
        table = resource.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"},  # Partition key
            ],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",  # On-demand — serverless, scales to zero
            SSESpecification=sse_spec,
            Tags=[
                {"Key": "Project", "Value": "ai-trading"},
                {"Key": "Component", "Value": "identity-verification"},
                {"Key": "DataClass", "Value": "confidential"},
            ],
        )
        # Wait for table to become active
        table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
        logger.info("DynamoDB table '%s' created with KMS encryption", table_name)

        # Enable Point-in-Time Recovery
        if settings.DYNAMODB_PITR_ENABLED:
            try:
                client = resource.meta.client
                client.update_continuous_backups(
                    TableName=table_name,
                    PointInTimeRecoverySpecification={
                        "PointInTimeRecoveryEnabled": True,
                    },
                )
                logger.info("PITR enabled on table '%s'", table_name)
            except Exception as pitr_exc:
                logger.warning("Failed to enable PITR: %s", pitr_exc)

        # Enable TTL attribute
        try:
            client = resource.meta.client
            client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    "AttributeName": "ttl",
                    "Enabled": True,
                },
            )
            logger.info("TTL enabled on table '%s' (attribute: ttl)", table_name)
        except Exception as ttl_exc:
            logger.warning("Failed to enable TTL: %s", ttl_exc)

        _table = table
        _table_verified = True
        return table

    except Exception as exc:
        logger.error("Failed to create DynamoDB table '%s': %s", table_name, exc)
        return None


# ─── Cloud Identity Store ──────────────────────────────────────────────────────

class CloudIdentityStore:
    """DynamoDB-backed identity store with KMS encryption at rest.

    All identity records are encrypted at rest using AWS KMS.
    Verified records persist indefinitely; unverified records auto-expire
    via DynamoDB TTL after DYNAMODB_TTL_DAYS_UNVERIFIED days.

    This store is the source of truth for real trading. The in-memory
    _verification_db in identity_verification.py serves as a local
    fallback/cache when DynamoDB is unavailable.
    """

    def __init__(self):
        self._enabled: Optional[bool] = None

    @property
    def enabled(self) -> bool:
        """Check if DynamoDB cloud storage is enabled and available."""
        if self._enabled is None:
            settings = get_settings()
            self._enabled = settings.DYNAMODB_ENABLED
        return self._enabled

    def _refresh_enabled(self):
        """Refresh the enabled flag (call after config changes)."""
        settings = get_settings()
        self._enabled = settings.DYNAMODB_ENABLED

    def put_identity(self, email: str, record: dict) -> bool:
        """Store or update an identity record in DynamoDB.

        Args:
            email: User's email (partition key).
            record: Full verification record dict from _verification_db.

        Returns:
            True if stored successfully, False otherwise.
        """
        if not self.enabled:
            return False

        table = _get_table()
        if table is None:
            logger.warning("DynamoDB table unavailable — skipping cloud sync for %s", email)
            return False

        settings = get_settings()

        try:
            # Build DynamoDB item from record
            item = self._record_to_item(email, record, settings)
            table.put_item(Item=item)
            logger.info(
                "Cloud identity stored for %s (provider=%s, verified=%s)",
                email, record.get("provider"), record.get("verified"),
            )
            return True
        except Exception as exc:
            logger.error("Failed to store identity in DynamoDB for %s: %s", email, exc)
            return False

    def get_identity(self, email: str) -> Optional[dict]:
        """Retrieve an identity record from DynamoDB.

        Args:
            email: User's email (partition key).

        Returns:
            Identity record dict, or None if not found / DynamoDB unavailable.
        """
        if not self.enabled:
            return None

        table = _get_table()
        if table is None:
            return None

        try:
            response = table.get_item(Key={"email": email.lower().strip()})
            item = response.get("Item")
            if item is None:
                return None
            return self._item_to_record(item)
        except Exception as exc:
            logger.error("Failed to get identity from DynamoDB for %s: %s", email, exc)
            return None

    def delete_identity(self, email: str) -> bool:
        """Delete an identity record from DynamoDB.

        Args:
            email: User's email (partition key).

        Returns:
            True if deleted successfully, False otherwise.
        """
        if not self.enabled:
            return False

        table = _get_table()
        if table is None:
            return False

        try:
            table.delete_item(Key={"email": email.lower().strip()})
            logger.info("Cloud identity deleted for %s", email)
            return True
        except Exception as exc:
            logger.error("Failed to delete identity from DynamoDB for %s: %s", email, exc)
            return False

    def list_identities(self, limit: int = 100) -> List[dict]:
        """List all identity records from DynamoDB (for admin use).

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of identity record dicts.
        """
        if not self.enabled:
            return []

        table = _get_table()
        if table is None:
            return []

        try:
            records = []
            response = table.scan(Limit=limit)
            for item in response.get("Items", []):
                records.append(self._item_to_record(item))
            return records
        except Exception as exc:
            logger.error("Failed to list identities from DynamoDB: %s", exc)
            return []

    def bulk_sync(self, local_db: dict) -> int:
        """Sync all records from local in-memory DB to DynamoDB.

        Called on startup to ensure cloud has the latest data.
        Uses PutItem which overwrites — last-write-wins per record.

        Args:
            local_db: The _verification_db dict from identity_verification.py.

        Returns:
            Number of records successfully synced.
        """
        if not self.enabled:
            return 0

        table = _get_table()
        if table is None:
            return 0

        settings = get_settings()
        synced = 0

        for email, record in local_db.items():
            try:
                item = self._record_to_item(email, record, settings)
                table.put_item(Item=item)
                synced += 1
            except Exception as exc:
                logger.error("Bulk sync failed for %s: %s", email, exc)

        logger.info("Bulk sync: %d/%d records synced to DynamoDB", synced, len(local_db))
        return synced

    def pull_to_local(self, local_db: dict) -> int:
        """Pull all records from DynamoDB into local in-memory DB.

        Called on startup to load persisted identities into the local cache.
        Existing local records are NOT overwritten if they're newer.

        Args:
            local_db: The _verification_db dict from identity_verification.py
                      (modified in place).

        Returns:
            Number of records pulled from cloud.
        """
        if not self.enabled:
            return 0

        table = _get_table()
        if table is None:
            return 0

        pulled = 0
        try:
            # Scan all items (paginated)
            response = table.scan()
            for item in response.get("Items", []):
                email = item.get("email", "").lower().strip()
                if not email:
                    continue
                record = self._item_to_record(item)
                # Only update local if cloud record is newer or local doesn't have it
                existing = local_db.get(email)
                if existing is None:
                    local_db[email] = record
                    pulled += 1
                else:
                    # Compare timestamps — cloud wins if newer
                    cloud_ts = record.get("verified_at", "")
                    local_ts = existing.get("verified_at", "")
                    if cloud_ts > local_ts:
                        local_db[email] = record
                        pulled += 1

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                for item in response.get("Items", []):
                    email = item.get("email", "").lower().strip()
                    if not email:
                        continue
                    record = self._item_to_record(item)
                    existing = local_db.get(email)
                    if existing is None:
                        local_db[email] = record
                        pulled += 1
                    else:
                        cloud_ts = record.get("verified_at", "")
                        local_ts = existing.get("verified_at", "")
                        if cloud_ts > local_ts:
                            local_db[email] = record
                            pulled += 1

        except Exception as exc:
            logger.error("Failed to pull identities from DynamoDB: %s", exc)

        logger.info("Pull from cloud: %d records loaded into local DB", pulled)
        return pulled

    # ─── Serialization Helpers ──────────────────────────────────────────────

    @staticmethod
    def _record_to_item(email: str, record: dict, settings) -> dict:
        """Convert a local verification record dict to a DynamoDB item.

        Adds TTL for unverified records and ensures all types are
        DynamoDB-compatible (no nested dicts with mixed types).
        """
        normalized_email = email.lower().strip()

        item: dict = {
            "email": normalized_email,
            "provider": record.get("provider", ""),
            "provider_username": record.get("provider_username", ""),
            "display_name": record.get("display_name", ""),
            "verified": record.get("verified", False),
            "verified_at": record.get("verified_at", ""),
            "reputation_score": record.get("reputation_score", 0.0),
            # Provider-specific identity (derived from GitHub + LinkedIn only)
            "github_username": record.get("github_username", ""),
            "linkedin_username": record.get("linkedin_username", ""),
            "github_display_name": record.get("github_display_name", ""),
            "linkedin_display_name": record.get("linkedin_display_name", ""),
            # Crypto experience
            "crypto_priority": record.get("crypto_priority", ""),
            "crypto_estimated_years": record.get("crypto_estimated_years", 0.0),
            "crypto_can_trade": record.get("crypto_can_trade", False),
            # Dual verification
            "dual_verified": record.get("dual_verified", False),
            # Metadata
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Serialize lists/dicts as JSON strings (DynamoDB doesn't support nested mixed types)
        crypto_signals = record.get("crypto_signals", [])
        if crypto_signals:
            item["crypto_signals_json"] = json.dumps(crypto_signals)

        providers = record.get("providers", [])
        if providers:
            item["providers_json"] = json.dumps(providers)

        # TTL: unverified records auto-expire after configured days
        if not record.get("verified", False):
            ttl_days = settings.DYNAMODB_TTL_DAYS_UNVERIFIED
            item["ttl"] = int(time.time()) + (ttl_days * 86400)
        # Verified records never expire (no ttl attribute = no expiration)

        return item

    @staticmethod
    def _item_to_record(item: dict) -> dict:
        """Convert a DynamoDB item back to a local verification record dict."""
        record: dict = {
            "provider": item.get("provider", ""),
            "provider_username": item.get("provider_username", ""),
            "display_name": item.get("display_name", ""),
            "verified": item.get("verified", False),
            "verified_at": item.get("verified_at", ""),
            "reputation_score": float(item.get("reputation_score", 0.0)),
            # Provider-specific identity
            "github_username": item.get("github_username", ""),
            "linkedin_username": item.get("linkedin_username", ""),
            "github_display_name": item.get("github_display_name", ""),
            "linkedin_display_name": item.get("linkedin_display_name", ""),
            # Crypto experience
            "crypto_priority": item.get("crypto_priority", ""),
            "crypto_estimated_years": float(item.get("crypto_estimated_years", 0.0)),
            "crypto_can_trade": item.get("crypto_can_trade", False),
            # Dual verification
            "dual_verified": item.get("dual_verified", False),
        }

        # Deserialize JSON fields
        crypto_signals_json = item.get("crypto_signals_json", "")
        if crypto_signals_json:
            try:
                record["crypto_signals"] = json.loads(crypto_signals_json)
            except (json.JSONDecodeError, TypeError):
                record["crypto_signals"] = []
        else:
            record["crypto_signals"] = []

        providers_json = item.get("providers_json", "")
        if providers_json:
            try:
                record["providers"] = json.loads(providers_json)
            except (json.JSONDecodeError, TypeError):
                record["providers"] = []
        else:
            record["providers"] = []

        return record


# ─── Module-level singleton ────────────────────────────────────────────────────

cloud_store = CloudIdentityStore()
"""Global CloudIdentityStore instance — use this throughout the app."""
