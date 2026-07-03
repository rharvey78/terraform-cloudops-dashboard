
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import boto3


dynamodb = boto3.resource("dynamodb")


TABLE_NAME = os.environ["TABLE_NAME"]
WORKLOADS_JSON = os.environ.get("WORKLOADS_JSON", "[]")
TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", "10"))

table = dynamodb.Table(TABLE_NAME)


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def check_url(workload):
    name = workload["name"]
    url = workload["url"]
    expected_status = int(workload.get("expected_status", 200))
    runbook_url = workload.get("runbook_url", "")

    started = time.perf_counter()
    checked_at = utc_now_iso()

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "cloudops-incident-dashboard-health-checker"
            },
            method="GET",
        )

        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            http_status = response.getcode()
            response.read(512)

        latency_ms = int((time.perf_counter() - started) * 1000)

        status = "healthy" if http_status == expected_status else "critical"
        message = (
            "Health check passed"
            if status == "healthy"
            else f"Unexpected HTTP status: {http_status}"
        )

    except urllib.error.HTTPError as error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        http_status = error.code
        status = "critical"
        message = f"HTTP error: {error.code}"

    except Exception as error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        http_status = 0
        status = "critical"
        message = f"Health check failed: {type(error).__name__}: {str(error)}"

    item = {
        "pk": f"WORKLOAD#{name}",
        "sk": "STATUS#LATEST",
        "workload_name": name,
        "url": url,
        "status": status,
        "http_status": http_status,
        "expected_status": expected_status,
        "latency_ms": latency_ms,
        "message": message,
        "checked_at": checked_at,
        "runbook_url": runbook_url,
    }

    table.put_item(Item=item)

    return item


def lambda_handler(event, context):
    workloads = json.loads(WORKLOADS_JSON)

    results = []
    for workload in workloads:
        results.append(check_url(workload))

    critical_count = sum(1 for item in results if item["status"] == "critical")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "checked_at": utc_now_iso(),
                "workloads_checked": len(results),
                "critical_count": critical_count,
                "results": results,
            }
        ),
    }