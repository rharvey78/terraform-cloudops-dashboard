
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import boto3


# Create AWS service clients/resources once when the Lambda container starts.
# Reusing them across warm Lambda invocations avoids unnecessary setup work.
dynamodb = boto3.resource("dynamodb")
cloudwatch = boto3.client("cloudwatch")


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


def validate_privateops_backend(response_body):
    """
    Validate the PrivateOps API response.

    A healthy PrivateOps backend must return the expected private-network
    architecture state along with the summary and detail sections required
    by the frontend dashboard.
    """
    try:
        payload = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return (
            "critical",
            f"PrivateOps API returned invalid JSON: {type(error).__name__}",
            {},
        )

    if not isinstance(payload, dict):
        return (
            "critical",
            "PrivateOps API response was not a JSON object",
            {},
        )

    # These values describe the expected architecture state of the demo.
    expected_values = {
        "backend_status": "private-backend-operational",
        "backend_exposure": "not-public",
        "vpc_mode": "cost-controlled-demo",
        "nat_gateway": "disabled",
        "s3_gateway_endpoint": "enabled",
        "dynamodb_gateway_endpoint": "enabled",
    }

    missing_fields = [
        field
        for field in expected_values
        if field not in payload
    ]

    if missing_fields:
        return (
            "critical",
            "PrivateOps response is missing required fields: "
            + ", ".join(missing_fields),
            {},
        )

    # Retain useful architecture values in the CloudOps status record.
    result_details = {
        field: payload.get(field)
        for field in expected_values
    }

    mismatches = [
        (
            f"{field} expected {expected_value}, "
            f"received {payload.get(field)}"
        )
        for field, expected_value in expected_values.items()
        if payload.get(field) != expected_value
    ]

    if mismatches:
        return (
            "critical",
            "PrivateOps architecture state mismatch: "
            + "; ".join(mismatches),
            result_details,
        )

    summary = payload.get("summary")

    if not isinstance(summary, dict):
        return (
            "critical",
            "PrivateOps response is missing the summary object",
            result_details,
        )

    required_summary_fields = (
        "service_count",
        "open_incidents",
        "pending_jobs",
        "recent_events",
    )

    missing_summary_fields = [
        field
        for field in required_summary_fields
        if field not in summary
    ]

    if missing_summary_fields:
        return (
            "critical",
            "PrivateOps summary is missing required fields: "
            + ", ".join(missing_summary_fields),
            result_details,
        )

    # Store the counts for troubleshooting and dashboard visibility.
    for field in required_summary_fields:
        value = summary.get(field)

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return (
                "critical",
                f"PrivateOps summary field {field} is not numeric",
                result_details,
            )

        result_details[field] = int(value)

    detail = payload.get("data")

    if not isinstance(detail, dict):
        return (
            "critical",
            "PrivateOps response is missing the data object",
            result_details,
        )

    required_detail_sections = (
        "service_health",
        "open_incidents",
        "pending_jobs",
        "recent_events",
        "architecture_status",
        "cost_guardrails",
    )

    invalid_detail_sections = [
        field
        for field in required_detail_sections
        if not isinstance(detail.get(field), list)
    ]

    if invalid_detail_sections:
        return (
            "critical",
            "PrivateOps response contains missing or invalid detail sections: "
            + ", ".join(invalid_detail_sections),
            result_details,
        )

    return (
        "healthy",
        (
            "PrivateOps backend healthy. "
            "API returned the expected private-backend state."
        ),
        result_details,
    )


def check_cloudwatch_alarms(workload):
    """
    Evaluate the CloudWatch alarms configured for an operational workload.

    A healthy workload requires:
      - At least one alarm name to be configured
      - Every configured alarm to exist
      - Every configured alarm to currently be in the OK state

    ALARM and INSUFFICIENT_DATA are both treated as critical because the
    CloudOps dashboard should only report healthy when monitoring can
    positively establish that the underlying workload is healthy.
    """
    alarm_names = workload.get("alarm_names") or []

    if not alarm_names:
        return (
            "critical",
            "No CloudWatch alarms are configured for this workload",
            {
                "alarms_checked": 0,
                "alarm_states": {},
            },
        )

    response = cloudwatch.describe_alarms(
        AlarmNames=alarm_names,
    )

    # DescribeAlarms can return metric alarms and composite alarms.
    returned_alarms = (
        response.get("MetricAlarms", [])
        + response.get("CompositeAlarms", [])
    )

    alarm_states = {
        alarm["AlarmName"]: alarm.get("StateValue", "UNKNOWN")
        for alarm in returned_alarms
        if "AlarmName" in alarm
    }

    result_details = {
        "alarms_checked": len(returned_alarms),
        "alarm_states": alarm_states,
    }

    # Detect configuration mistakes such as an alarm being renamed or deleted.
    missing_alarms = [
        alarm_name
        for alarm_name in alarm_names
        if alarm_name not in alarm_states
    ]

    if missing_alarms:
        return (
            "critical",
            "CloudWatch alarm not found: " + ", ".join(missing_alarms),
            result_details,
        )

    alarmed = [
        alarm_name
        for alarm_name, state in alarm_states.items()
        if state == "ALARM"
    ]

    if alarmed:
        return (
            "critical",
            "CloudWatch alarm is in ALARM state: " + ", ".join(alarmed),
            result_details,
        )

    insufficient_data = [
        alarm_name
        for alarm_name, state in alarm_states.items()
        if state != "OK"
    ]

    if insufficient_data:
        return (
            "critical",
            "CloudWatch alarm is not in OK state: "
            + ", ".join(insufficient_data),
            result_details,
        )

    return (
        "healthy",
        "All configured CloudWatch alarms are OK",
        result_details,
    )


def check_url(workload):
    """
    Run one configured workload health check.

    HTTP-based workloads continue to use their configured endpoint.

    CloudWatch alarm-based workloads bypass HTTP completely and inspect
    existing CloudWatch alarm state instead. This prevents operational
    monitoring from unnecessarily invoking workload APIs or downstream
    services such as Amazon Timestream.
    """
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
        # CloudWatch alarm checks intentionally bypass the workload's HTTP
        # endpoint. The existing alarms have already evaluated operational
        # health, so there is no reason to query the application data path.
        if check_type == "cloudwatch_alarms":
            status, message, result_details = check_cloudwatch_alarms(
                workload
            )

            latency_ms = int((time.perf_counter() - started) * 1000)

            # No HTTP request was made for this check type.
            http_status = 0

        else:
            # All existing HTTP-based workload types continue to use their
            # configured endpoint and response-validation logic.
            request = create_request(workload)

            with urllib.request.urlopen(
                request,
                timeout=TIMEOUT_SECONDS,
            ) as response:
                http_status = response.getcode()

                # API responses are expected to be small. Impose a reasonable
                # limit so the checker does not read an unlimited response body.
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

            elif check_type == "privateops_backend":
                status, message, result_details = validate_privateops_backend(
                    response_body=response_body,
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

    # Add workload-specific values such as CloudWatch alarm states,
    # observation age, or PrivateOps architecture details.
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