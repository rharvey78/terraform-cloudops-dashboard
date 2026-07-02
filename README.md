# CloudOps Incident Dashboard

CloudOps Incident Dashboard is a low-cost AWS operations demo built to monitor the health of my AWS portfolio workloads.

The project focuses on cloud operations rather than application development. It checks workload availability, stores health status, triggers alerts, records operational issues, and links failures to simple runbooks.

## Business Problem

Small cloud environments often have several workloads running but no simple operational view showing what is healthy, what is failing, and what should be checked first.

This project demonstrates how a lightweight AWS operations layer can improve visibility, incident response, and reliability without adding expensive always-on infrastructure.

## Core AWS Services

- EventBridge Scheduler
- AWS Lambda
- Amazon DynamoDB
- Amazon API Gateway HTTP API
- Amazon CloudWatch
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

## Operational Goals

- Monitor existing portfolio workloads
- Detect failed health checks
- Store latest workload status
- Send alerts when failures occur
- Link failures to runbooks
- Demonstrate practical CloudOps skills
