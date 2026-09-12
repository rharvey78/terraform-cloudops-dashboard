# Weather API / Data Pipeline Failure Runbook

## Service

Weather Dashboard and Weather Data Pipeline

## Purpose

This runbook provides first-response troubleshooting steps when the CloudOps Incident Dashboard reports the weather workload as unhealthy.

The weather workload is not monitored by repeatedly querying Amazon Timestream. Routine CloudOps checks inspect existing CloudWatch alarm states instead. This avoids creating unnecessary database-query cost while still preserving operational visibility.

## Monitoring Model

The CloudOps Health Checker evaluates the CloudWatch alarms configured for the weather workload.

A healthy result requires every configured alarm to exist and report `OK`.

The current weather monitoring pattern includes alarms for:

- Weather-ingestion freshness
- IoT ingestion silence

Typical configured alarms include:

```text
wx-IngestFreshnessSeconds>300
iot-ingestion-silent-5m
```

If an alarm is in `ALARM`, `INSUFFICIENT_DATA`, or cannot be found, the CloudOps workload is reported as `critical`.

## Symptoms

The CloudOps dashboard may report one or more of the following:

- Weather data pipeline status is `critical`
- One or more configured CloudWatch alarms are not `OK`
- Weather data shown on the dashboard is stale
- New sensor observations stop appearing
- IoT ingestion appears silent
- The weather API still responds but returns old data
- A supporting Lambda function reports errors

## First Checks

### 1. Identify the Alarm State

Review the CloudOps health result for the weather workload.

Look for:

- `status`
- `message`
- `alarms_checked`
- `alarm_states`
- `checked_at`

The failure message should identify whether an alarm is in `ALARM`, is not in `OK`, or is missing.

You can also review the relevant CloudWatch alarms directly in the AWS console.

### 2. Check CloudWatch Alarms from PowerShell

If the AWS CLI is configured locally, inspect the current alarm states:

```powershell
aws cloudwatch describe-alarms `
  --alarm-names `
  "wx-IngestFreshnessSeconds>300" `
  "iot-ingestion-silent-5m" `
  --query "MetricAlarms[].{AlarmName:AlarmName,State:StateValue,Reason:StateReason}" |
  ConvertFrom-Json |
  Format-List
```

Expected healthy state:

```text
State : OK
```

If one alarm is in `ALARM`, troubleshoot the failure domain represented by that alarm instead of immediately changing the monitoring system.

### 3. Determine Whether Ingestion Has Stopped

If the IoT-ingestion alarm is active, check the path from the weather station toward AWS.

Review:

- Weather station console / sensor availability
- Raspberry Pi process state
- SDR / `rtl_433` reception
- Network connectivity from the Raspberry Pi
- MQTT publishing to AWS IoT Core
- AWS IoT rule activity
- Ingest Lambda errors

The goal is to identify the earliest point where current observations stop flowing.

### 4. Check the Ingest Lambda

Review the CloudWatch Logs for the weather-ingest Lambda around the alarm time.

Look for:

- Lambda execution errors
- Parsing failures
- AWS IoT payload problems
- Timestream write errors
- Permission errors
- Throttling

If the Lambda is succeeding but freshness still degrades, continue downstream to the data store or timestamp handling.

### 5. Check Data Freshness

The freshness alarm is intended to detect when the newest weather observation becomes too old.

Confirm whether recent data is reaching the storage layer before assuming the dashboard itself is broken.

Do not repeatedly call the Timestream-backed weather API as a routine health check. Use it only when a direct data-path test is needed during troubleshooting.

## Manual Data-Path Validation

If CloudWatch indicates a problem and you need to confirm the application data path, perform a single manual weather API request.

Use the existing weather API endpoint and request a small range such as `1h`.

Example PowerShell pattern:

```powershell
$body = @{
    query_range = "1h"
    tz          = "America/Chicago"
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "<weather-api-endpoint>" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body

$response | Format-List
```

Replace `<weather-api-endpoint>` with the deployed endpoint used by the weather dashboard.

Check whether the response contains recent observations and whether the newest timestamp is current.

A manual API call is diagnostic. It should not become the recurring CloudOps monitoring mechanism because it can create unnecessary downstream query cost.

## Failure Domains

### Edge / Sensor Failure

Possible indicators:

- No recent `rtl_433` observations
- Raspberry Pi process stopped
- SDR not receiving the WH65B weather sensor
- Local networking problem

Recovery should focus on restoring local sensor reception and the sender process before changing AWS resources.

### AWS IoT Ingestion Failure

Possible indicators:

- Local sensor data exists
- MQTT publish attempts fail
- AWS IoT rule does not receive or process messages

Check AWS IoT Core configuration, rule metrics, permissions, and Lambda invocation behavior.

### Ingest Lambda Failure

Possible indicators:

- AWS IoT receives messages
- Lambda errors appear in CloudWatch
- No new Timestream writes occur

Review the Lambda error before changing permissions or deployment configuration.

### Timestream Write / Data Failure

Possible indicators:

- Ingest Lambda is invoked
- Write errors appear in logs
- Recent observations do not appear in the data store

Check Timestream table availability, write errors, schema expectations, timestamp values, and IAM permissions.

### Dashboard / API Failure

Possible indicators:

- Recent observations exist in the data store
- Weather API returns errors or stale results
- Dashboard does not display current data

Inspect the weather API Lambda, API Gateway, frontend request, and cached/precomputed data as appropriate.

## Recovery Principles

Use the least disruptive fix that addresses the confirmed failure.

- Restart an edge process only when the process is actually stopped or unhealthy.
- Correct IAM only when logs show a permission failure.
- Do not recreate AWS resources as a first troubleshooting step.
- Avoid speculative changes to IoT rules, Lambda configuration, or Timestream resources.
- Make Terraform-managed infrastructure changes through the normal Terraform workflow whenever practical.
- If an emergency console change is required, reconcile Terraform afterward.

## Verification

After corrective action, verify recovery from the bottom of the pipeline upward.

### 1. Confirm Current Sensor Data

Verify that the edge device is again receiving current weather observations.

### 2. Confirm AWS Ingestion

Confirm that AWS IoT and the ingest Lambda are processing new observations without errors.

### 3. Confirm Alarm Recovery

Check that the configured weather alarms return to:

```text
OK
```

### 4. Confirm CloudOps Recovery

Confirm that the next CloudOps health check reports the weather workload as:

```text
status = healthy
```

and that the recorded alarm states are `OK`.

### 5. Confirm Dashboard Data

Open the weather dashboard and verify that current observations are visible and timestamps are advancing normally.

## Incident Notes

For a meaningful outage, record:

- Detection time
- Alarm that detected the failure
- User-visible impact
- Failure domain
- Root cause, if known
- Corrective action
- Recovery time
- Verification performed
- Follow-up work required

Also note whether the incident revealed an opportunity to improve alarms, logging, runbooks, or cost control.
