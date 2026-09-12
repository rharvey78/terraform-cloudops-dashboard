# CloudOps Incident Dashboard

A low-cost AWS CloudOps monitoring and incident-response demo built with Terraform, AWS Lambda, CloudWatch, DynamoDB, API Gateway, EventBridge, and SNS.

The project focuses on the operational side of cloud workloads: checking health, detecting failures, distinguishing stale monitoring data from healthy data, storing current status, exposing that status through an API, alerting on problems, and linking incidents to practical runbooks.

The goal is not to reproduce an enterprise monitoring platform. It is to demonstrate real CloudOps patterns in a small AWS environment while keeping recurring cost under control.

## What This Project Demonstrates

- Scheduled multi-workload health checks
- HTTP endpoint monitoring
- Workload-specific response validation
- CloudWatch alarm-state monitoring
- DynamoDB-backed operational state
- Stale-monitoring detection
- Public status API for dashboard use
- CloudWatch custom metrics and alarms
- SNS email notifications
- Runbook-driven incident response
- Least-privilege IAM where AWS supports resource scoping
- Terraform-managed infrastructure
- Cost-aware monitoring design

## Architecture Overview

The EventBridge schedule invokes a Health Checker Lambda. Each configured workload defines how it should be evaluated.

```text
EventBridge scheduled rule
        |
        v
Health Checker Lambda
        |
        +--> HTTP health checks
        |
        +--> Workload-specific response validation
        |
        +--> CloudWatch alarm-state checks
        |
        v
DynamoDB latest-status records
        |
        +--> Structured CloudWatch log summary
        |        |
        |        v
        |   CloudWatch Logs metric filter
        |        |
        |        v
        |   WorkloadCriticalCount metric
        |        |
        |        v
        |   CloudWatch alarm
        |        |
        |        v
        |      SNS alert
        |
        v
Status API Lambda
        |
        v
API Gateway HTTP API
        |
        v
CloudOps dashboard
```

The Status API also evaluates the age of each stored health record. If monitoring data becomes too old, the API reports the workload as `stale` instead of continuing to present an old result as current.

## Health-Check Types

The Health Checker supports several operational patterns through the `workloads` Terraform variable.

### Standard HTTP Check

For a normal website or API endpoint, the checker sends the configured request and validates the expected HTTP response code.

Typical use:

```text
GET endpoint
    -> expected HTTP 200
    -> healthy / critical
```

### PrivateOps Backend Validation

The PrivateOps check goes beyond HTTP status. It validates that the backend returns the expected architecture state and required response sections.

Examples of validated state include:

- private backend is operational
- backend exposure is not public
- NAT Gateway remains disabled
- S3 gateway endpoint is enabled
- DynamoDB gateway endpoint is enabled

This allows the monitor to verify expected application and architecture state instead of treating every HTTP 200 response as automatically healthy.

### CloudWatch Alarm-State Check

Operational workloads can be monitored by inspecting existing CloudWatch alarms rather than calling the workload's application data path.

A healthy alarm-based check requires:

- configured alarms exist
- every configured alarm reports `OK`

`ALARM`, `INSUFFICIENT_DATA`, or a missing alarm is treated as a critical result.

This pattern is currently used for weather-pipeline monitoring so routine CloudOps checks do not unnecessarily invoke the Timestream-backed weather data API.

## Cost Optimization: Weather Monitoring Redesign

An earlier version of the CloudOps checker validated the weather data pipeline by calling the weather API on every scheduled health check.

That worked technically, but the API query caused Amazon Timestream to execute a query even when no user was viewing the weather dashboard. Routine monitoring was therefore creating avoidable database-query cost.

The monitoring design was changed so the CloudOps Health Checker reads the state of existing weather-related CloudWatch alarms instead.

```text
Before

Scheduled CloudOps check
        -> Weather API
        -> Timestream query
        -> Health result

After

Scheduled CloudOps check
        -> CloudWatch DescribeAlarms
        -> Existing ingestion/freshness alarms
        -> Health result
```

The redesign preserves operational visibility while removing monitoring-generated Timestream queries from the recurring health-check path.

This is an intentional design principle in the project: monitoring should provide useful signal without creating unnecessary workload or cost of its own.

## Operational State in DynamoDB

The Health Checker stores the latest result for each workload using a simple key pattern:

```text
pk = WORKLOAD#<workload-name>
sk = STATUS#LATEST
```

A stored result can include values such as:

- workload name
- check type
- status
- HTTP status
- expected status
- latency
- timestamp
- runbook URL
- CloudWatch alarm states
- workload-specific validation details

The project intentionally stores current operational state rather than building a large historical monitoring database.

## Status API and Freshness Detection

The Status API Lambda reads the latest workload records from DynamoDB and returns them through API Gateway.

It also evaluates monitoring freshness.

If a health record is older than the configured stale threshold, the API changes the public status to `stale` and preserves the previous status as `original_status`.

Conceptually:

```json
{
  "workload_name": "portfolio-homepage",
  "status": "stale",
  "original_status": "healthy",
  "is_stale": true,
  "age_minutes": 130
}
```

This prevents an old successful health check from being mistaken for proof that the workload is still healthy.

## Alerting Model

The project separates monitoring-system failures from monitored-workload failures.

### Monitoring System Failure

A CloudWatch alarm monitors Lambda execution errors for the Health Checker itself.

```text
Health Checker Lambda error
        -> AWS/Lambda Errors metric
        -> CloudWatch alarm
        -> SNS notification
```

This answers:

```text
Did the monitoring system itself fail?
```

### Workload Health Failure

After each Health Checker run, a structured summary is written to CloudWatch Logs.

Example:

```json
{
  "event_type": "health_check_summary",
  "workloads_checked": 4,
  "critical_count": 0
}
```

A CloudWatch Logs metric filter extracts `critical_count` and publishes the custom metric:

```text
Namespace: CloudOpsIncidentDashboard
Metric:    WorkloadCriticalCount
```

The workload alarm enters `ALARM` when one or more workloads report critical status.

This answers:

```text
Did a monitored workload fail even though the monitoring Lambda ran successfully?
```

That distinction is important because successful execution of a monitoring function does not mean the systems being monitored are healthy.

## Incident Simulation

The alert path was tested with an intentional failure scenario.

A temporary workload used the correct site URL but an intentionally incorrect expected HTTP status:

```text
Actual response:   200
Expected response: 418
Result:            critical
```

The test confirmed the full alert path:

1. Health Checker detected the mismatch.
2. DynamoDB recorded the critical state.
3. The structured summary reported `critical_count = 1`.
4. The custom CloudWatch metric updated.
5. The workload alarm moved to `ALARM`.
6. SNS delivered an alert notification.
7. After the test condition was removed, monitoring returned to normal.

## Runbooks

The repository includes first-response runbooks for several portfolio workloads:

- [Portfolio homepage failure](runbooks/portfolio-homepage-failure.md)
- [Weather API / data pipeline failure](runbooks/weather-api-failure.md)
- [Dog Breed API failure](runbooks/dog-breed-api-failure.md)
- [RonBot failure](runbooks/ronbot-failure.md)
- [Contact form failure](runbooks/contact-form-failure.md)

The purpose of the runbooks is not to automate every recovery action. They provide a disciplined starting point: verify the symptom, identify the failure domain, make the least disruptive correction, and confirm recovery.

## Core AWS Services

- Amazon EventBridge
- AWS Lambda
- Amazon DynamoDB
- Amazon API Gateway HTTP API
- Amazon CloudWatch
- Amazon CloudWatch Logs
- Amazon SNS
- AWS Identity and Access Management (IAM)

## Cost-Control Decisions

The project intentionally avoids expensive always-on infrastructure.

Current design choices include:

- No NAT Gateway for this monitoring stack
- No EC2 instances
- No RDS database
- No EKS cluster
- DynamoDB on-demand billing
- Low-frequency scheduled health checks
- Short CloudWatch log retention
- Small Lambda memory allocations
- Serverless services where practical
- CloudWatch alarm-state monitoring where direct application queries would create unnecessary downstream cost

The project treats cost as an operational constraint rather than something to review only after deployment.

## Terraform

Infrastructure is managed with Terraform and deployed through a remote Terraform workspace.

Terraform manages:

- Lambda functions and deployment packages
- IAM execution roles and policies
- DynamoDB status table
- API Gateway HTTP API
- EventBridge scheduled rule
- CloudWatch log groups
- CloudWatch Logs metric filter
- CloudWatch alarms
- SNS topic and email subscription

Workload definitions are supplied through the `workloads` variable rather than being hard-coded into the Lambda source.

## Repository Structure

```text
.
|-- README.md
|-- api_gateway.tf
|-- cloudwatch.tf
|-- dynamodb.tf
|-- eventbridge.tf
|-- iam.tf
|-- lambda.tf
|-- main.tf
|-- outputs.tf
|-- providers.tf
|-- sns.tf
|-- variables.tf
|-- lambda_src/
|   |-- health_checker.py
|   `-- status_api.py
`-- runbooks/
    |-- portfolio-homepage-failure.md
    |-- weather-api-failure.md
    |-- dog-breed-api-failure.md
    |-- ronbot-failure.md
    `-- contact-form-failure.md
```

## Design Principles

This project follows a few deliberate operational principles:

1. **Monitoring must be monitored.** A failed monitoring function and a failed workload are different incidents.
2. **A successful HTTP response is not always enough.** Workload-specific checks validate expected behavior and state when practical.
3. **Old health data is not current health.** Stale results are identified explicitly.
4. **Use existing signals when they are sufficient.** CloudWatch alarm state can be more efficient than repeatedly querying an application data path.
5. **Keep permissions narrow.** IAM access is scoped to required resources where AWS APIs support resource-level permissions.
6. **Prefer the least disruptive recovery action.** Runbooks encourage isolating the problem before changing infrastructure.
7. **Cost is part of reliability engineering.** Monitoring should not create unnecessary recurring workload or spend.

## Why This Project Matters

This project is intentionally small, but the operational pattern is real.

It demonstrates the work I enjoy most in cloud environments:

- tracing failures across service boundaries
- reading logs and alarm state
- validating IAM and configuration
- distinguishing application failures from monitoring failures
- restoring service without unnecessary changes
- documenting repeatable response paths
- improving reliability while keeping cost under control

The project is designed as a practical CloudOps portfolio example rather than a software-development showcase.
