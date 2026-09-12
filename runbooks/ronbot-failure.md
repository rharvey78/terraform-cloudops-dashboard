# RonBot Failure Runbook

## Service

RonBot Portfolio Chatbot

## Purpose

This runbook provides first-response troubleshooting steps when RonBot is unavailable, returns errors, fails to match expected intents, or does not complete fulfillment correctly.

RonBot uses Amazon Lex for conversational intent handling and an AWS Lambda function for fulfillment logic.

## Symptoms

Possible symptoms include:

- Chatbot does not respond
- Lex returns an error to the frontend
- User input consistently falls back to an unintended response
- A known intent is not recognized
- Fulfillment Lambda returns an error
- A specific intent works incorrectly while others continue to work
- The frontend cannot communicate with the bot
- CloudWatch shows Lambda errors or throttling

## First Checks

### 1. Confirm the Chatbot Page Is Reachable

Open the RonBot page from the portfolio site and verify that the page loads normally.

If the page itself does not load, troubleshoot the portfolio website before the chatbot backend.

### 2. Reproduce with a Known Intent

Use a simple prompt that should map to a known RonBot intent.

Examples include prompts about:

- Portfolio projects
- Technologies used
- Weather project
- Dog Breed Identifier
- SentimentPulse
- Resume
- Target roles

Record:

- Time of the test
- User message
- Bot response
- Whether the failure affects one intent or all intents

This helps distinguish a general service failure from an intent-specific configuration problem.

### 3. Check Amazon Lex

Review the active bot alias and locale configuration in Amazon Lex.

Confirm:

- The expected bot alias is available
- The intended bot version is associated with the alias
- The `en_US` locale is built and available
- The affected intent exists and is enabled
- Recent configuration changes did not remove or alter expected sample utterances or fulfillment settings

If only one intent is failing, inspect that intent before changing the entire bot configuration.

### 4. Check the Fulfillment Lambda

Review CloudWatch Logs for the RonBot fulfillment Lambda around the failure time.

Look for:

- Unhandled exceptions
- Missing intent handlers
- Invalid request structure
- Unexpected slot values
- Permission errors
- Runtime errors
- Throttling

Use the Lex request timestamp to correlate the conversation failure with the corresponding Lambda invocation.

### 5. Confirm Lex-to-Lambda Integration

If Lex recognizes the intent but fulfillment fails, verify the Lambda integration.

Confirm:

- The correct Lambda function is configured for fulfillment
- Lex has permission to invoke the Lambda
- The Lambda handler is responding in the format expected by Lex
- The active bot alias/version references the intended configuration

Do not change IAM permissions unless the logs indicate an invocation or permission failure.

### 6. Distinguish Recognition from Fulfillment Problems

A useful first split is:

```text
Wrong intent / fallback response -> Lex recognition/configuration
Correct intent but error response -> Lambda fulfillment/integration
No chatbot response at all       -> frontend, Lex access, or broader service path
```

This prevents unnecessary changes to the fulfillment Lambda when the real problem is intent recognition, or vice versa.

## Failure Domains

### Frontend Failure

Possible indicators:

- Chat interface does not load
- Browser request fails before reaching Lex
- JavaScript error appears in the browser console

Troubleshoot the frontend request path before changing Lex or Lambda.

### Intent Recognition Failure

Possible indicators:

- Bot responds, but the wrong intent is selected
- Known prompts fall back unexpectedly
- Only one topic is affected

Review sample utterances, intent configuration, slot definitions, and the active bot version.

### Fulfillment Lambda Failure

Possible indicators:

- Correct intent is recognized
- Lex invokes fulfillment
- User receives an error or empty response
- CloudWatch logs show an exception

Use the Lambda error to isolate the specific handler or response-construction problem.

### Integration / Permission Failure

Possible indicators:

- Lex recognizes the intent
- Lambda is not invoked
- Lex reports a fulfillment error

Check the Lex alias configuration, Lambda association, and invoke permissions.

## Recovery Principles

Use the least disruptive fix that addresses the confirmed failure.

- Fix one affected intent without rebuilding unrelated intents.
- Correct Lambda logic only when fulfillment is the confirmed failure domain.
- Do not broaden IAM permissions as a first response.
- Preserve the currently working bot alias/version relationship unless the failure is isolated to deployment configuration.
- Make Terraform-managed changes through the normal Terraform workflow whenever practical.
- If an emergency console change is required, reconcile Terraform afterward.

## Verification

After corrective action:

1. Open the RonBot page.
2. Test a known-good intent.
3. Test the previously failing intent.
4. Confirm the bot returns the expected response.
5. Confirm no new Lambda errors appear in CloudWatch.
6. Confirm unrelated intents still work.

If the CloudOps dashboard monitors RonBot, confirm the next health check returns the workload to `healthy`.

## Incident Notes

For a meaningful outage, record:

- Detection time
- User-visible impact
- Affected intent or function
- Lex or Lambda error details
- Root cause, if known
- Corrective action
- Verification performed
- Follow-up work required

The goal is to identify whether the failure is in the frontend, intent recognition, fulfillment logic, or integration path and restore service without introducing unrelated changes.
