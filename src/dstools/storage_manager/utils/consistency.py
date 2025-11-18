"""
Consistency checking and repair utilities.

This module provides utilities for checking and repairing consistency
between database storage and object store.
"""

from typing import Dict, Any, List, Optional
import logging

from ..db.base import BaseDBStorage
from ..object_store.base import BaseObjectStore
from ..exceptions import ConsistencyError


logger = logging.getLogger(__name__)


def check_consistency(
    db_storage: BaseDBStorage,
    object_store: BaseObjectStore,
    collection: str,
    object_key_field: str = "object_key",
) -> Dict[str, Any]:
    """
    Check consistency between database and object store.

    Args:
        db_storage: Database storage instance
        object_store: Object store instance
        collection: Collection/table name
        object_key_field: Field name for object key

    Returns:
        Dictionary with consistency check results
    """
    issues = {
        "missing_objects": [],  # Records without objects
        "orphaned_objects": [],  # Objects without records
        "invalid_references": [],  # Records with invalid object references
    }

    # Check records for missing or invalid object references
    records = db_storage.query(collection)
    record_object_keys = set()

    for record in records:
        record_id = record.get("id")
        object_key = record.get(object_key_field)

        if not object_key:
            issues["invalid_references"].append(
                {
                    "record_id": record_id,
                    "reason": "missing object_key field",
                }
            )
            continue

        record_object_keys.add(object_key)

        # Check if object exists
        if not object_store.exists(object_key):
            issues["missing_objects"].append(
                {
                    "record_id": record_id,
                    "object_key": object_key,
                }
            )

    # Check for orphaned objects
    object_keys = set(object_store.list_objects())

    for object_key in object_keys:
        if object_key not in record_object_keys:
            issues["orphaned_objects"].append(object_key)

    return {
        "status": "complete",
        "total_records": len(records),
        "total_objects": len(object_keys),
        "issues_found": (
            len(issues["missing_objects"])
            + len(issues["orphaned_objects"])
            + len(issues["invalid_references"])
        ),
        "issues": issues,
    }


def repair_consistency(
    db_storage: BaseDBStorage,
    object_store: BaseObjectStore,
    collection: str,
    object_key_field: str = "object_key",
    remove_orphans: bool = True,
    remove_invalid_records: bool = False,
) -> Dict[str, Any]:
    """
    Repair consistency issues between database and object store.

    Args:
        db_storage: Database storage instance
        object_store: Object store instance
        collection: Collection/table name
        object_key_field: Field name for object key
        remove_orphans: Remove orphaned objects
        remove_invalid_records: Remove records with missing objects

    Returns:
        Dictionary with repair results
    """
    # First, check consistency
    consistency_report = check_consistency(
        db_storage, object_store, collection, object_key_field
    )

    results = {
        "orphans_deleted": 0,
        "invalid_records_deleted": 0,
        "errors": [],
    }

    # Remove orphaned objects
    if remove_orphans:
        for object_key in consistency_report["issues"]["orphaned_objects"]:
            try:
                object_store.delete(object_key)
                results["orphans_deleted"] += 1
            except Exception as e:
                logger.error(f"Failed to delete orphaned object '{object_key}': {e}")
                results["errors"].append(
                    {
                        "type": "delete_orphan",
                        "object_key": object_key,
                        "error": str(e),
                    }
                )

    # Remove invalid records
    if remove_invalid_records:
        # Records with missing objects
        for issue in consistency_report["issues"]["missing_objects"]:
            record_id = issue["record_id"]
            try:
                db_storage.delete(collection, record_id)
                results["invalid_records_deleted"] += 1
            except Exception as e:
                logger.error(f"Failed to delete invalid record '{record_id}': {e}")
                results["errors"].append(
                    {
                        "type": "delete_record",
                        "record_id": record_id,
                        "error": str(e),
                    }
                )

        # Records with invalid references
        for issue in consistency_report["issues"]["invalid_references"]:
            record_id = issue["record_id"]
            try:
                db_storage.delete(collection, record_id)
                results["invalid_records_deleted"] += 1
            except Exception as e:
                logger.error(f"Failed to delete invalid record '{record_id}': {e}")
                results["errors"].append(
                    {
                        "type": "delete_record",
                        "record_id": record_id,
                        "error": str(e),
                    }
                )

    return results


def find_orphaned_objects(
    db_storage: BaseDBStorage,
    object_store: BaseObjectStore,
    collection: str,
    object_key_field: str = "object_key",
) -> List[str]:
    """
    Find orphaned objects (objects without DB records).

    Args:
        db_storage: Database storage instance
        object_store: Object store instance
        collection: Collection/table name
        object_key_field: Field name for object key

    Returns:
        List of orphaned object keys
    """
    # Get all object keys referenced by records
    records = db_storage.query(collection)
    record_object_keys = {
        record.get(object_key_field)
        for record in records
        if record.get(object_key_field)
    }

    # Get all object keys from object store
    object_keys = set(object_store.list_objects())

    # Find orphans
    orphaned = object_keys - record_object_keys

    return list(orphaned)


def find_missing_objects(
    db_storage: BaseDBStorage,
    object_store: BaseObjectStore,
    collection: str,
    object_key_field: str = "object_key",
) -> List[Dict[str, Any]]:
    """
    Find records with missing objects.

    Args:
        db_storage: Database storage instance
        object_store: Object store instance
        collection: Collection/table name
        object_key_field: Field name for object key

    Returns:
        List of records with missing objects
    """
    missing = []

    records = db_storage.query(collection)

    for record in records:
        object_key = record.get(object_key_field)
        if object_key and not object_store.exists(object_key):
            missing.append(
                {
                    "record_id": record.get("id"),
                    "object_key": object_key,
                    "record": record,
                }
            )

    return missing
