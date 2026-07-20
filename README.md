# CloudOps Incident Dashboard

CloudOps Incident Dashboard is a low-cost AWS operations demo built to monitor the health of my AWS portfolio workloads.

The project focuses on cloud operations rather than application development. It checks workload availability, stores the latest health status, exposes that status through an API, sends SNS email alerts when failures occur, and links operational issues to simple runbooks.

## Business Problem

Small cloud environments often have several workloads running, but no simple operational view showing what is healthy, what is failing, and what should be checked first.

This project demonstrates how a lightweight AWS operations layer can improve visibility, incident response, and reliability without adding expensive always-on infrastructure.

## What This Project Demonstrates

- Scheduled workload health checks
- Serverless status collection
- DynamoDB-backed operational state
- Public status API for dashboard use
- CloudWatch alarms for both monitoring failures and workload failures
- SNS email notifications
- Simple runbook-driven incident response
- Terraform-managed AWS infrastructure
- Cost-conscious CloudOps design

## Architecture Overview

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