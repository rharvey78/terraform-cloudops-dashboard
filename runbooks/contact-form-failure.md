# Contact Form Failure Runbook

## Service

Portfolio Contact Form

## Purpose

This runbook provides first-response troubleshooting steps when the portfolio contact form cannot submit a message successfully or when a submitted message does not reach the expected destination.

The exact backend implementation may evolve, so this runbook focuses on isolating the failure domain from browser submission through the serverless backend and final message delivery.

## Symptoms

Possible symptoms include:

- Contact page does not load
- Submit button does nothing
- Browser shows a JavaScript error
- Form request returns a 4xx or 5xx response
- Backend Lambda returns an error
- Submission appears successful but no message is delivered
- CORS blocks the request
- CloudWatch shows Lambda errors or throttling

## First Checks

### 1. Confirm the Contact Page Is Reachable

Open the portfolio contact page and verify that it loads normally.

If the page itself does not load, troubleshoot the portfolio website before the form backend.

### 2. Submit a Controlled Test Message

Use a simple test submission with valid data.

Record:

- Time of submission
- Name used
- Email used
- Whether the browser displayed success or failure
- HTTP status, if visible
- Whether the message was ultimately delivered

Avoid repeated submissions while troubleshooting so duplicate messages do not create confusion.

### 3. Check the Browser Request

Use the browser developer tools Network tab and submit the form once.

Check:

- Request URL
- HTTP method
- HTTP status
- Request payload
- Response body
- CORS errors

This determines whether the failure occurs before or after the request reaches the backend.

### 4. Check the API Endpoint

If the frontend request is sent successfully, review the API layer handling the contact request.

Look for:

- 4xx responses caused by malformed or rejected input
- 5xx responses caused by backend integration failures
- Incorrect route or method configuration
- CORS configuration problems
- Integration timeout or invocation errors

Use the request timestamp to correlate API activity with Lambda logs.

### 5. Check the Backend Lambda

Review CloudWatch Logs for the contact-form Lambda around the test time.

Look for:

- Unhandled exceptions
- Input validation errors
- Missing environment variables
- Permission errors
- Message-delivery service errors
- Runtime errors
- Throttling

Do not broaden IAM permissions unless the logs identify a permission failure.

### 6. Check Message Delivery

If the API and Lambda complete successfully but the message is not received, isolate the delivery layer.

Confirm:

- The backend reports a successful send operation
- The configured destination is correct
- No delivery-service error is present in the logs
- The receiving mailbox did not classify the message as spam or junk
- Any required sender/domain verification remains valid

A successful API response does not by itself prove successful final delivery.

## Failure Domains

### Frontend Failure

Possible indicators:

- Submit action never sends a request
- JavaScript error appears
- Form validation blocks valid input

Focus on the contact-page JavaScript and form configuration before changing AWS resources.

### API / CORS Failure

Possible indicators:

- Browser sends the request
- Request is blocked by CORS or returns 4xx/5xx
- Lambda is not invoked

Check the API route, allowed origins, allowed methods, integration configuration, and deployment state.

### Lambda Failure

Possible indicators:

- API invokes the backend
- CloudWatch logs show an exception
- Response returns 5xx

Use the Lambda error to determine whether the issue is request parsing, configuration, permissions, or downstream delivery.

### Delivery Failure

Possible indicators:

- Lambda completes successfully
- Frontend shows success
- Message never reaches the destination

Check the message-delivery provider, destination address, verification state, bounce/rejection information, and mailbox filtering.

## Recovery Principles

Use the least disruptive fix that addresses the confirmed failure.

- Correct input validation only when valid requests are being rejected.
- Fix CORS at the API/frontend boundary instead of bypassing browser security controls.
- Do not broaden IAM permissions as a first response.
- Do not repeatedly send test submissions once one clean test provides the information needed.
- Make Terraform-managed infrastructure changes through the normal Terraform workflow whenever practical.
- If an emergency console change is required, reconcile Terraform afterward.

## Verification

After corrective action:

1. Open the contact page.
2. Submit one controlled test message.
3. Confirm the browser reports success.
4. Confirm the API returns the expected successful response.
5. Confirm no new Lambda errors appear in CloudWatch.
6. Confirm the message reaches the expected destination.

If the CloudOps dashboard monitors the contact form, confirm the next health check returns the workload to `healthy`.

## Incident Notes

For a meaningful outage, record:

- Detection time
- User-visible impact
- HTTP status or browser error
- Failed component
- Root cause, if known
- Corrective action
- Delivery verification
- Follow-up work required

The goal is to trace the request from browser to final delivery and fix the actual failed layer without introducing unnecessary changes elsewhere.
