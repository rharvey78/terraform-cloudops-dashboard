
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3


# Create the DynamoDB service resource.
dynamodb = boto3.resource("dynamodb")

# Read Lambda configuration from environment variables.
TABLE_NAME = os.environ["TABLE_NAME"]
STALE_AFTER_MINUTES = int(
    os.environ.get("STALE_AFTER_MINUTES", "120")
)

# Reference the CloudOps status table.
table = dynamodb.Table(TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    """
    Convert DynamoDB Decimal values into standard JSON numbers.
    """

    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)

        return super().default(obj)


def parse_checked_at(value):
    """
    Convert a stored ISO 8601 checked_at value into a UTC datetime.

    Returns None when the timestamp is missing or invalid.
    """
    if not isinstance(value, str) or not value:
        return None

    normalized_value = value

    # Support timestamps ending in Z as well as timestamps ending in +00:00.
    if normalized_value.endswith("Z"):
        normalized_value = normalized_value[:-1] + "+00:00"

    try:
        checked_at = datetime.fromisoformat(normalized_value)
    except ValueError:
        return None

    # Treat timestamps without timezone information as UTC.
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)

    return checked_at.astimezone(timezone.utc)


def add_freshness_status(item, evaluated_at):
    """
    Add freshness information to one stored workload result.

    When the stored checked_at value is older than STALE_AFTER_MINUTES,
    the API returns the workload status as stale.
    """
    result = dict(item)

    checked_at = parse_checked_at(
        item.get("checked_at")
    )

    # A missing or invalid timestamp cannot be trusted.
    if checked_at is None:
        result["original_status"] = item.get(
            "status",
            "unknown",
        )
        result["status"] = "stale"
        result["is_stale"] = True
        result["age_minutes"] = None
        result["message"] = (
            "Monitoring data is stale because checked_at "
            "is missing or invalid."
        )

        return result

    age_seconds = max(
        0,
        (evaluated_at - checked_at).total_seconds(),
    )

    age_minutes = int(age_seconds // 60)

    is_stale = (
        age_seconds
        >= STALE_AFTER_MINUTES * 60
    )

    result["is_stale"] = is_stale
    result["age_minutes"] = age_minutes

    # Preserve the previous health state before changing the public status.
    if is_stale:
        result["original_status"] = item.get(
            "status",
            "unknown",
        )
        result["status"] = "stale"
        result["message"] = (
            f"Monitoring data is stale. "
            f"The last check was {age_minutes} minutes ago."
        )

    return result


def lambda_handler(event, context):
    """
    Read the latest workload records from DynamoDB and return them
    through the public CloudOps Status API.
    """
    response = table.scan()

    items = response.get(
        "Items",
        [],
    )

    # Keep only the latest workload status records.
    workload_statuses = [
        item
        for item in items
        if item.get("pk", "").startswith("WORKLOAD#")
        and item.get("sk") == "STATUS#LATEST"
    ]

    evaluated_at = datetime.now(
        timezone.utc
    )

    # Add freshness information to each stored workload result.
    workload_statuses = [
        add_freshness_status(
            item,
            evaluated_at,
        )
        for item in workload_statuses
    ]

    # Keep the API response ordering predictable.
    workload_statuses.sort(
        key=lambda item: item.get(
            "workload_name",
            "",
        )
    )

    stale_count = sum(
        1
        for item in workload_statuses
        if item.get("is_stale") is True
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(
            {
                "evaluated_at": evaluated_at.isoformat(),
                "stale_after_minutes": STALE_AFTER_MINUTES,
                "workload_count": len(workload_statuses),
                "stale_count": stale_count,
                "workloads": workload_statuses,
            },
            cls=DecimalEncoder,
        ),
    }