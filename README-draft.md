# CloudOps Incident Dashboard

CloudOps Incident Dashboard is a low-cost AWS operations demo built to monitor the health of my AWS portfolio workloads.

The project focuses on cloud operations rather than application development. It checks workload availability, stores the latest health status, exposes that status through an API, sends alerts when failures occur, and links operational issues to simple runbooks.

## Business Problem

Small cloud environments often have several workloads running, but no simple operational view showing what is healthy, what is failing, and what should be checked first.

This project demonstrates how a lightweight AWS operations layer can improve visibility, incident response, and reliability without adding expensive always-on infrastructure.

## What This Project Demonstrates

- Scheduled workload health checks
- Serverless status collection
- DynamoDB-backed operational state
- Public status API for dashboard use
- CloudWatch alarms for monitoring failures
- CloudWatch alarms for workload failures
- SNS email notifications
- Simple runbook-driven incident response
- Terraform-managed AWS infrastructure
- Cost-conscious CloudOps design

## Architecture Overview

The Health Checker Lambda runs on a schedule and checks configured workload URLs.

```text
EventBridge scheduled rule
        ↓
Health Checker Lambda
        ↓
Checks portfolio workload URLs
        ↓
Stores latest status in DynamoDB
        ↓
Emits structured CloudWatch log events
        ↓
CloudWatch Logs metric filter
        ↓
Custom CloudWatch metric
        ↓
CloudWatch alarm
        ↓
SNS email alert
```

The latest workload status is exposed through an API Gateway HTTP API backed by a separate Lambda function.

```text
Browser / Dashboard
        ↓
API Gateway HTTP API
        ↓
Status API Lambda
        ↓
DynamoDB status table
        ↓
JSON health response
```

## Core AWS Services

- Amazon EventBridge
- AWS Lambda
- Amazon DynamoDB
- Amazon API Gateway HTTP API
- Amazon CloudWatch
- Amazon CloudWatch Logs
- Amazon SNS
- AWS Budgets
- IAM

## Design Constraints

- Terraform-managed infrastructure
- No NAT Gateway
- No EC2
- No RDS
- No EKS
- Low-frequency health checks
- Short CloudWatch log retention
- Cost-conscious architecture

## Current Monitored Workload

The current health check monitors my main AWS portfolio site:

```text
https://c-comp.net/
```

Expected result:

```text
HTTP 200 OK
```

The latest workload state is stored in DynamoDB using a simple status record pattern:

```text
pk = WORKLOAD#portfolio-homepage
sk = STATUS#LATEST
```

## Status API

The Status API returns the latest workload health state from DynamoDB.

Example healthy response:

```json
{
  "workload_count": 1,
  "workloads": [
    {
      "workload_name": "portfolio-homepage",
      "url": "https://c-comp.net/",
      "status": "healthy",
      "http_status": 200,
      "expected_status": 200,
      "message": "Health check passed"
    }
  ]
}
```

## Alerting Model

This project separates two different operational failure types.

### 1. Monitoring System Failure

This alarm detects whether the Health Checker Lambda itself fails.

```text
Health Checker Lambda error
        ↓
CloudWatch Lambda Errors metric
        ↓
CloudWatch alarm
        ↓
SNS email notification
```

This answers:

```text
Did the monitoring system break?
```

### 2. Workload Health Failure

This alarm detects whether one or more monitored workloads are unhealthy.

```text
Health Checker Lambda succeeds
        ↓
Workload check reports critical status
        ↓
critical_count is written to CloudWatch Logs
        ↓
CloudWatch Logs metric filter extracts WorkloadCriticalCount
        ↓
CloudWatch alarm
        ↓
SNS email notification
```

This answers:

```text
Did a monitored workload fail?
```

That distinction matters because the monitoring Lambda can run successfully while still detecting that a workload is unhealthy.

## Custom CloudWatch Metric

The Health Checker emits a structured log event after each run.

Example:

```json
{
  "event_type": "health_check_summary",
  "checked_at": "2026-07-20T22:10:50.000831+00:00",
  "workloads_checked": 1,
  "critical_count": 0
}
```

A CloudWatch Logs metric filter extracts `critical_count` and publishes it as a custom metric:

```text
Namespace: CloudOpsIncidentDashboard
Metric:    WorkloadCriticalCount
```

The workload alarm triggers when:

```text
WorkloadCriticalCount >= 1
```

The workload alarm currently uses a 5-minute evaluation period so testing and recovery can be observed without waiting for a full one-hour CloudWatch period.

## Tested Incident Simulation

The workload alert path was tested with an intentional failure scenario.

A temporary test workload was added using the correct site URL but an intentionally wrong expected status code:

```text
Actual response:   200
Expected response: 418
Result:            critical
```

This safely simulated a workload failure without breaking the real site.

The test confirmed:

- Health Checker Lambda detected the mismatch
- DynamoDB recorded the workload as critical
- CloudWatch Logs emitted `critical_count = 1`
- The custom CloudWatch metric updated
- The workload alarm moved to ALARM
- SNS sent an email notification
- After removing the test workload, the system returned to OK

## Runbooks

Simple runbooks are included for common portfolio workload failures.

Current runbooks include:

- Weather API failure
- Dog breed API failure
- RonBot failure
- Contact form failure

The goal is not just to detect a problem, but to provide a first place to look when something fails.

## Cost Control

This project intentionally avoids expensive always-on infrastructure.

Cost-conscious choices include:

- No NAT Gateway
- No EC2 instances
- No RDS databases
- No EKS cluster
- DynamoDB on-demand billing
- Low-frequency scheduled checks
- Short CloudWatch log retention
- Small Lambda functions
- Serverless services where practical

## Terraform

All infrastructure is managed with Terraform and deployed through Terraform Cloud.

Terraform manages:

- Lambda functions
- IAM roles and least-privilege policies
- DynamoDB table
- API Gateway HTTP API
- EventBridge scheduled rule
- CloudWatch log groups
- CloudWatch Logs metric filter
- CloudWatch alarms
- SNS topic and email subscription
- AWS Budget resources

## Current Project Status

Current tested status:

```text
Health Checker Lambda: working
Status API Lambda: working
DynamoDB status table: clean
CloudWatch metric filter: working
Custom CloudWatch metric: working
Lambda error alarm: OK
Workload critical alarm: OK
SNS email notifications: tested
```

## Why This Project Matters

This project represents the kind of practical CloudOps work I enjoy:

- watching systems
- detecting failures
- separating signal from noise
- keeping costs under control
- documenting response paths
- making cloud workloads easier to support

It is intentionally small, but the operational pattern is real.