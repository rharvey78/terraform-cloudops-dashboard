
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import boto3


# Create the DynamoDB service resource once when the Lambda container starts.
dynamodb = boto3.resource("dynamodb")


# Values supplied to the Lambda function through Terraform.
TABLE_NAME = os.environ["TABLE_NAME"]
WORKLOADS_JSON = os.environ.get("WORKLOADS_JSON", "[]")
TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", "10"))

# DynamoDB table where the latest workload results are stored.
table = dynamodb.Table(TABLE_NAME)


def utc_now():
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_iso():
    """Return the current UTC time in ISO 8601 format."""
    return utc_now().isoformat()


def create_request(workload):
    """
    Build the HTTP request described by the workload configuration.

    Ordinary website checks use GET. API checks may use POST with a
    JSON request body.
    """
    url = workload["url"]
    method = str(workload.get("method", "GET")).upper()
    request_body = workload.get("request_body") or {}

    headers = {
        "User-Agent": "cloudops-incident-dashboard-health-checker",
        "Accept": "application/json",
    }

    request_data = None

    if method in {"POST", "PUT", "PATCH"}:
        request_data = json.dumps(request_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    return urllib.request.Request(
        url,
        data=request_data,
        headers=headers,
        method=method,
    )


def validate_weather_pipeline(
    response_body,
    max_data_age_minutes,
    evaluated_at,
):
    """
    Validate the Weather Station API response.

    A healthy pipeline must return:
      - Valid JSON
      - ok set to true
      - At least one weather observation
      - Required weather fields
      - A recent observation timestamp
    """
    try:
        payload = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return (
            "critical",
            f"Weather API returned invalid JSON: {type(error).__name__}",
            {},
        )

    if not isinstance(payload, dict):
        return (
            "critical",
            "Weather API response was not a JSON object",
            {},
        )

    if payload.get("ok") is not True:
        return (
            "critical",
            "Weather API did not report ok=true",
            {},
        )

    rows = payload.get("rows")

    if not isinstance(rows, list) or not rows:
        return (
            "critical",
            "Weather API returned no observation rows",
            {
                "rows_returned": 0,
                "max_data_age_minutes": max_data_age_minutes,
            },
        )

    # Keep only rows containing a numeric millisecond timestamp.
    timestamped_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and isinstance(row.get("ts_ms"), (int, float))
        and not isinstance(row.get("ts_ms"), bool)
    ]

    if not timestamped_rows:
        return (
            "critical",
            "Weather API returned no valid observation timestamps",
            {
                "rows_returned": len(rows),
                "max_data_age_minutes": max_data_age_minutes,
            },
        )

    # The newest observation is the best indication of current ingestion.
    newest_row = max(timestamped_rows, key=lambda row: row["ts_ms"])

    required_fields = (
        "temperature_F",
        "humidity",
        "wind_mph",
        "battery_ok",
    )

    missing_fields = [
        field
        for field in required_fields
        if field not in newest_row or newest_row[field] is None
    ]

    if missing_fields:
        return (
            "critical",
            "Newest weather observation is missing required fields: "
            + ", ".join(missing_fields),
            {
                "rows_returned": len(rows),
                "max_data_age_minutes": max_data_age_minutes,
            },
        )

    try:
        observation_time = datetime.fromtimestamp(
            float(newest_row["ts_ms"]) / 1000,
            tz=timezone.utc,
        )
    except (OSError, OverflowError, TypeError, ValueError):
        return (
            "critical",
            "Newest weather observation contains an invalid timestamp",
            {
                "rows_returned": len(rows),
                "max_data_age_minutes": max_data_age_minutes,
            },
        )

    age_seconds = (evaluated_at - observation_time).total_seconds()

    # Allow a small amount of clock difference, but reject timestamps that
    # appear substantially ahead of the Lambda function's clock.
    if age_seconds < -300:
        future_minutes = int(abs(age_seconds) // 60)

        return (
            "critical",
            (
                "Newest weather observation timestamp is "
                f"{future_minutes} minutes in the future"
            ),
            {
                "rows_returned": len(rows),
                "data_timestamp": observation_time.isoformat(),
                "data_age_minutes": 0,
                "max_data_age_minutes": max_data_age_minutes,
            },
        )

    # Minor clock differences are represented as zero minutes old.
    age_seconds = max(age_seconds, 0)
    age_minutes = int(age_seconds // 60)

    result_details = {
        "rows_returned": len(rows),
        "data_timestamp": observation_time.isoformat(),
        "data_age_minutes": age_minutes,
        "max_data_age_minutes": max_data_age_minutes,
    }

    if age_seconds > max_data_age_minutes * 60:
        return (
            "critical",
            (
                "Weather data is stale. "
                f"The newest observation is {age_minutes} minutes old."
            ),
            result_details,
        )

    age_description = (
        "less than 1 minute old"
        if age_minutes == 0
        else f"{age_minutes} minute{'s' if age_minutes != 1 else ''} old"
    )

    return (
        "healthy",
        f"Weather pipeline healthy. Newest observation is {age_description}.",
        result_details,
    )


def check_url(workload):
    """Run one configured workload health check."""
    name = workload["name"]
    url = workload["url"]
    expected_status = int(workload.get("expected_status", 200))
    runbook_url = workload.get("runbook_url", "")
    method = str(workload.get("method", "GET")).upper()
    check_type = str(workload.get("check_type", "http")).lower()
    max_data_age_minutes = int(
        workload.get("max_data_age_minutes", 5)
    )

    started = time.perf_counter()
    evaluated_at = utc_now()
    checked_at = evaluated_at.isoformat()

    # Workload-specific details are added to the DynamoDB item when available.
    result_details = {}

    try:
        request = create_request(workload)

        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:
            http_status = response.getcode()

            # The Weather response is small, but impose a reasonable maximum
            # so the health checker does not read an unlimited response body.
            response_body = response.read(1_000_000)

        latency_ms = int((time.perf_counter() - started) * 1000)

        if http_status != expected_status:
            status = "critical"
            message = f"Unexpected HTTP status: {http_status}"

        elif check_type == "http":
            status = "healthy"
            message = "Health check passed"

        elif check_type == "weather_pipeline":
            status, message, result_details = validate_weather_pipeline(
                response_body=response_body,
                max_data_age_minutes=max_data_age_minutes,
                evaluated_at=evaluated_at,
            )

        else:
            status = "critical"
            message = f"Unsupported check type: {check_type}"

    except urllib.error.HTTPError as error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        http_status = error.code
        status = "critical"
        message = f"HTTP error: {error.code}"

    except Exception as error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        http_status = 0
        status = "critical"
        message = (
            f"Health check failed: "
            f"{type(error).__name__}: {str(error)}"
        )

    item = {
        "pk": f"WORKLOAD#{name}",
        "sk": "STATUS#LATEST",
        "workload_name": name,
        "url": url,
        "request_method": method,
        "check_type": check_type,
        "status": status,
        "http_status": http_status,
        "expected_status": expected_status,
        "latency_ms": latency_ms,
        "message": message,
        "checked_at": checked_at,
        "runbook_url": runbook_url,
    }

    # Add pipeline-specific values such as observation age without changing
    # the records produced by ordinary HTTP checks.
    item.update(result_details)

    table.put_item(Item=item)

    return item


def lambda_handler(event, context):
    """Run every configured workload check and return a summary."""
    workloads = json.loads(WORKLOADS_JSON)

    results = []

    for workload in workloads:
        results.append(check_url(workload))

    critical_count = sum(
        1
        for item in results
        if item["status"] == "critical"
    )

    summary = {
        "event_type": "health_check_summary",
        "checked_at": utc_now_iso(),
        "workloads_checked": len(results),
        "critical_count": critical_count,
    }

    # This structured log event is used by the CloudWatch metric filter.
    print(json.dumps(summary))

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "checked_at": summary["checked_at"],
                "workloads_checked": len(results),
                "critical_count": critical_count,
                "results": results,
            }
        ),
    }