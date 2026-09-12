# Weather Dashboard Failure Runbook

## Service

Weather Dashboard

## Purpose

This runbook provides first-response troubleshooting steps when the CloudOps Incident Dashboard reports the public Weather Dashboard as unhealthy or when users cannot successfully access or use the weather page.

This runbook is specifically for the user-facing dashboard and its web-delivery path.

It does **not** cover failures in weather-station ingestion, AWS IoT Core, the ingest Lambda, Timestream, or weather-data freshness. Those failures should be investigated using the separate **Weather API / Data Pipeline Failure Runbook**.

## Monitoring Model

The CloudOps Health Checker monitors the Weather Dashboard as an HTTP workload.

A healthy result indicates that the configured dashboard URL responded successfully to the health check.

This confirms basic web availability, but it does not prove that the underlying weather-data pipeline is healthy or that current observations are flowing.

The dashboard and the data pipeline are therefore monitored separately.

## Symptoms

The CloudOps dashboard or a user may report one or more of the following:

- Weather Dashboard status is `critical`
- `weather.html` does not load
- Browser displays an HTTP or connection error
- Page loads incompletely
- Styles or JavaScript assets fail to load
- Dashboard controls or charts do not function
- Weather data does not appear even though the page itself loads
- Browser developer tools show failed network requests
- The page loads but displays stale or missing weather information

## First Checks

### 1. Review the CloudOps Health Result

Review the CloudOps status for the Weather Dashboard workload.

Look for:

- `status`
- `message`
- `http_status`
- `latency_ms`
- `checked_at`

Determine whether the health check failed because the dashboard URL was unreachable, returned an unexpected HTTP response, or encountered another request failure.

Do not immediately assume that a Weather Dashboard failure means the underlying weather-data pipeline has failed.

### 2. Open the Dashboard Directly

Open:

```text
https://c-comp.net/weather.html
```

Verify whether:

- The page loads
- The header and page styling appear normally
- Dashboard controls are visible
- Current weather information appears
- Charts and tables render
- Browser navigation works normally

If the page loads successfully, compare the current browser behavior with the CloudOps result before making infrastructure changes.

A temporary network or delivery problem may have recovered by the time manual testing begins.

### 3. Check the Base Website

Open:

```text
https://c-comp.net/
```

If both the portfolio homepage and Weather Dashboard are unavailable, investigate the shared website-delivery path before troubleshooting `weather.html` specifically.

If the portfolio homepage works but `weather.html` does not, the failure is more likely isolated to the Weather Dashboard page, its assets, or its application requests.

### 4. Check Browser Developer Tools

If the page loads incorrectly, open the browser developer tools and review the **Console** and **Network** tabs.

Look for:

- JavaScript errors
- Failed HTTP requests
- `4xx` or `5xx` responses
- Missing HTML, JavaScript, CSS, or data files
- API request failures
- CORS-related errors
- Unexpected cached responses

Identify the first failed request rather than treating later errors as separate failures when they may be consequences of the same root cause.

### 5. Determine Whether the Problem Is Frontend or Data Pipeline

If the page itself loads normally but weather information is stale, missing, or incomplete, determine whether the failure is actually in the underlying data path.

Indicators of a possible data-pipeline problem include:

- Weather page returns HTTP `200`
- Static page content loads correctly
- CSS and JavaScript assets load normally
- Current observations are missing
- Observation timestamps stop advancing
- Weather-data API requests fail or return stale information
- CloudWatch weather-ingestion or freshness alarms are not `OK`

If these conditions are present, stop troubleshooting the dashboard delivery layer and continue with the **Weather API / Data Pipeline Failure Runbook**.

## Failure Domains

### CloudFront / Static Website Delivery

Possible indicators:

- Weather Dashboard does not load
- Portfolio homepage may also be unavailable
- Browser receives an HTTP error
- Static assets return failed requests
- Recently deployed content is not being served as expected

Review:

- CloudFront distribution availability
- CloudFront request behavior
- S3 origin availability
- Object existence
- Object permissions and access configuration
- Recent infrastructure or deployment changes

Avoid changing CloudFront or S3 configuration until the failing request and expected behavior have been identified.

### Weather Page / Frontend Failure

Possible indicators:

- Portfolio homepage loads normally
- `weather.html` fails or renders incorrectly
- Browser console shows JavaScript errors
- Required page assets fail to load
- Dashboard controls or charts do not function

Review:

- `weather.html`
- Referenced JavaScript and CSS files
- Recent frontend changes
- Browser Console errors
- Network requests generated by the page

If a recent deployment introduced the failure, identify the specific changed component before reverting or redeploying.

### API Connectivity Failure

Possible indicators:

- Static dashboard loads normally
- API-backed sections fail
- Browser Network tab shows failed API requests
- HTTP errors are returned by API Gateway or a backend function

Determine whether the request failure is caused by:

- API Gateway
- Backend Lambda
- IAM or permissions
- Request format
- CORS or browser access
- Backend dependency failure

If the API failure involves weather-data freshness, ingestion, or Timestream, transfer troubleshooting to the **Weather API / Data Pipeline Failure Runbook**.

### Cached or Precomputed Weather Data

Possible indicators:

- Dashboard loads normally
- Some longer-range weather information is missing or stale
- Current observations may still work
- Static or precomputed data files are not updating as expected

Review the relevant precompute process, generated data files, timestamps, and supporting Lambda logs before changing the frontend.

A stale data file is a data-generation problem rather than evidence that CloudFront or the Weather Dashboard page itself has failed.

## Recovery Principles

Use the least disruptive correction that addresses the confirmed failure.

- Identify the failed layer before changing infrastructure.
- Do not invalidate or modify CloudFront configuration simply because weather data is stale.
- Do not change IAM unless logs or failed requests indicate an authorization problem.
- Do not recreate S3, CloudFront, API Gateway, or Lambda resources as a first troubleshooting step.
- Separate frontend availability failures from weather-data pipeline failures.
- Make Terraform-managed infrastructure changes through the normal Terraform workflow whenever practical.
- If an emergency console change is required, reconcile Terraform afterward.

## Verification

After corrective action, verify recovery from the user-facing layer and then confirm that the dashboard is displaying valid data.

### 1. Confirm Website Delivery

Open:

```text
https://c-comp.net/weather.html
```

Confirm that the page loads without an HTTP or browser error.

### 2. Confirm Frontend Assets

Verify that:

- Page styling loads correctly
- JavaScript executes without significant console errors
- Dashboard controls work
- Charts and tables render as expected

### 3. Confirm Application Requests

Use the browser Network tab to confirm that required application and data requests complete successfully.

There should be no unexplained failed requests affecting normal dashboard operation.

### 4. Confirm Current Data

Verify that current weather information is displayed and that observation timestamps are advancing normally.

If data remains stale even though the dashboard itself is working, continue troubleshooting with the **Weather API / Data Pipeline Failure Runbook**.

### 5. Confirm CloudOps Recovery

Confirm that the next CloudOps health check reports the Weather Dashboard workload as:

```text
status = healthy
```

Verify that the result reflects a successful current health check rather than an old status record.

## Incident Notes

For a meaningful outage, record:

- Detection time
- User-visible impact
- HTTP status or browser symptom
- Failure domain
- Root cause, if known
- Corrective action
- Recovery time
- Verification performed
- Whether the weather-data pipeline was also affected
- Follow-up work required

Also note whether the incident revealed an opportunity to improve monitoring, logging, frontend validation, deployment practices, or documentation.
