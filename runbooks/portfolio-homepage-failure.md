# Portfolio Homepage Failure Runbook

## Service

Portfolio Homepage

## URL

https://c-comp.net/

## Expected Result

HTTP 200 OK

## Purpose

This runbook provides first-check troubleshooting steps when the CloudOps Incident Dashboard reports the portfolio homepage as unhealthy.

## Symptoms

The Health Checker may report one of the following:

- The site does not return HTTP 200
- The request times out
- DNS resolution fails
- CloudFront returns an error
- The S3-backed static site is unavailable
- The status API reports the workload as `critical`

## First Checks

### 1. Confirm the Site Is Reachable

Open the site in a browser:

```text
https://c-comp.net/