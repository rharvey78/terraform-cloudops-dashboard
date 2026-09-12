# Portfolio Homepage Failure Runbook

## Service

Portfolio Homepage

## URL

https://c-comp.net/

## Expected Result

HTTP 200 OK

## Purpose

This runbook provides first-response troubleshooting steps when the CloudOps Incident Dashboard reports the portfolio homepage as unhealthy.

The site is a static website delivered through Amazon CloudFront with content stored in Amazon S3. DNS is hosted in Amazon Route 53 and HTTPS is provided through AWS Certificate Manager (ACM).

## Symptoms

The Health Checker may report one or more of the following:

- The site does not return HTTP 200
- The request times out
- DNS resolution fails
- CloudFront returns a 4xx or 5xx error
- The S3 origin cannot serve the requested content
- HTTPS certificate validation fails
- The CloudOps status API reports the workload as `critical`

## First Checks

### 1. Confirm the Site Is Reachable

Open the site in a browser:

```text
https://c-comp.net/
```

Then test the HTTP response from PowerShell:

```powershell
$response = Invoke-WebRequest -Uri "https://c-comp.net/" -Method Get
$response.StatusCode
```

Expected result:

```text
200
```

If the browser works but the health check still reports a failure, compare the failure timestamp with the most recent successful check. The incident may have been temporary.

### 2. Check DNS Resolution

Confirm that the domain resolves:

```powershell
Resolve-DnsName c-comp.net
```

Expected result:

- DNS resolution succeeds
- The response ultimately points to the CloudFront distribution

If DNS resolution fails, review the Route 53 hosted zone and the record used for `c-comp.net`.

### 3. Check CloudFront

In the AWS console, review the CloudFront distribution serving `c-comp.net`.

Confirm:

- The distribution is enabled
- The distribution status is deployed
- The configured alternate domain name includes `c-comp.net`
- The origin points to the expected S3 bucket
- There are no recent configuration changes that could explain the failure

If CloudFront is returning an error, note the HTTP status before making changes.

Common indicators:

- `403` can indicate an S3 origin-access or object-permission problem
- `404` can indicate a missing object or incorrect default root object
- `502`, `503`, or `504` can indicate an upstream/origin problem or temporary AWS service issue

### 4. Check the S3 Origin

Confirm that the portfolio bucket and expected homepage object still exist.

Verify:

- The S3 bucket exists
- `index.html` exists
- The object has not been accidentally deleted or replaced
- CloudFront still has permission to retrieve objects from the bucket

Do not make the bucket public as a troubleshooting shortcut.

### 5. Check HTTPS / ACM

If the site fails only over HTTPS, review the ACM certificate associated with the CloudFront distribution.

Confirm:

- Certificate status is `Issued`
- The certificate includes `c-comp.net`
- The certificate is attached to the correct CloudFront distribution

For CloudFront, the ACM certificate must be in `us-east-1`.

## CloudWatch and CloudOps Checks

Review the CloudOps health-check result and identify:

- `checked_at`
- `http_status`
- `latency_ms`
- `message`
- `status`

Also check the Health Checker Lambda logs in CloudWatch for the same timestamp.

Determine whether the failure is:

- A real website outage
- A DNS problem
- A CloudFront/origin problem
- A TLS/certificate problem
- A temporary network timeout
- A monitoring-system problem

Do not treat a single failed health check as proof of a persistent outage without validating the site independently.

## Recovery Actions

Choose the least disruptive action that addresses the confirmed failure.

### Missing or Incorrect S3 Content

Restore the correct static-site files to the S3 bucket through the normal deployment process.

If CloudFront continues serving an old or incorrect object after the S3 object is corrected, create a CloudFront invalidation only when necessary.

### CloudFront Configuration Problem

If a recent configuration change caused the issue:

1. Identify the exact change.
2. Correct or roll back that change through the normal Terraform workflow where the resource is Terraform-managed.
3. Allow the CloudFront distribution to finish deploying.
4. Retest the site.

Avoid making unmanaged console changes to Terraform-managed resources unless immediate recovery requires it. If an emergency console change is made, reconcile Terraform afterward.

### DNS Problem

Correct the Route 53 record only after confirming the expected CloudFront target.

Avoid speculative DNS changes because cached DNS responses can make troubleshooting more confusing.

### Certificate Problem

Confirm the correct ACM certificate is issued in `us-east-1` and associated with the CloudFront distribution.

Do not replace a working certificate unless the failure has been isolated to TLS/certificate configuration.

## Verification

After corrective action, verify the service from more than one layer.

### Browser Check

Open:

```text
https://c-comp.net/
```

Confirm the page loads normally over HTTPS.

### PowerShell Check

```powershell
$response = Invoke-WebRequest -Uri "https://c-comp.net/" -Method Get
$response | Select-Object StatusCode, StatusDescription
```

Expected result:

```text
StatusCode        : 200
StatusDescription : OK
```

### CloudOps Check

Confirm that the next scheduled CloudOps health check reports:

```text
status      = healthy
http_status = 200
```

Also confirm that any related CloudWatch alarm returns to `OK` when its evaluation criteria are satisfied.

## Incident Notes

Document the following when the failure is more than a brief transient event:

- Detection time
- User-visible impact
- Failure domain
- Root cause, if known
- Corrective action
- Verification performed
- Any follow-up work required

The goal is not only to restore the site, but also to make the next similar failure faster to diagnose and recover from.
