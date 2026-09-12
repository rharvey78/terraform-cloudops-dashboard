# Dog Breed API Failure Runbook

## Service

Dog Breed Identifier

## Purpose

This runbook provides first-response troubleshooting steps when the CloudOps Incident Dashboard or user testing indicates that the Dog Breed Identifier is not functioning correctly.

The application uses a browser upload flow backed by Amazon S3, Lambda, API Gateway, Amazon Rekognition, and DynamoDB. A presign Lambda generates the upload request used by the frontend.

## Symptoms

Possible symptoms include:

- Image upload fails
- Presigned upload request cannot be obtained
- S3 upload returns an error
- Prediction API returns an error
- Rekognition does not return usable labels
- Prediction results are not written to DynamoDB
- Frontend displays no result or an error message
- API Gateway or Lambda returns a 4xx or 5xx response

## First Checks

### 1. Confirm the Frontend Is Reachable

Open the Dog Breed Identifier page from the portfolio site and verify that the page loads normally.

If the page itself does not load, troubleshoot the portfolio website before the application backend.

### 2. Reproduce with a Known-Good Image

Use a normal JPG or PNG image containing a clearly visible dog.

Avoid troubleshooting first with an unusually large, corrupted, unsupported, or ambiguous image.

Record:

- Time of the test
- File type
- Whether the upload completed
- Any browser error message
- Any HTTP status returned

### 3. Check the Presign Lambda

The frontend first requires a valid presigned S3 upload request.

Review the presign Lambda logs in CloudWatch around the failure time.

Look for:

- Lambda execution errors
- S3 permission errors
- Invalid bucket configuration
- Malformed presigned POST data
- Runtime or dependency errors

If the presign step fails, fix that path before troubleshooting Rekognition or DynamoDB.

### 4. Check the S3 Upload

Confirm that the uploaded image reaches the expected S3 bucket.

Verify:

- The bucket exists
- The object was created
- The object key looks correct
- The uploaded object is readable by the backend role that needs it

Do not make the bucket public as a troubleshooting shortcut.

### 5. Check API Gateway

Review API Gateway metrics and access logs for the prediction request.

Look for:

- 4xx responses indicating request or authorization problems
- 5xx responses indicating integration or backend failures
- Integration latency spikes
- Missing or malformed request data

Use the request timestamp to correlate API Gateway activity with Lambda logs.

### 6. Check the Prediction Lambda

Review CloudWatch Logs for the Dog Breed prediction Lambda.

Look for:

- Unhandled exceptions
- S3 object access failures
- Rekognition API errors
- DynamoDB write errors
- IAM permission failures
- Throttling
- Unexpected input format

Do not broaden IAM permissions until a log entry identifies a permission failure.

### 7. Check Amazon Rekognition

If the Lambda successfully reads the image but no useful prediction is returned, verify the Rekognition call.

Confirm:

- The request reaches Rekognition
- The image format is supported
- Rekognition returns labels
- The application correctly interprets those labels

A successful Rekognition call does not guarantee that every image will produce a useful dog-breed result. Distinguish a service failure from a low-confidence or ambiguous prediction.

### 8. Check DynamoDB

If a prediction succeeds but the application cannot persist or retrieve the result, review the DynamoDB operation.

Confirm:

- The expected table exists
- The Lambda execution role has the required table permissions
- The write request succeeds
- No validation error is reported

## Failure Domains

### Presign Failure

Possible indicators:

- Upload cannot begin
- Presign Lambda errors
- Invalid or expired upload fields

Focus on the presign Lambda, S3 target configuration, and IAM permissions.

### S3 Upload Failure

Possible indicators:

- Presign request succeeds
- Browser upload fails
- Object never appears in S3

Check the presigned POST conditions, object size/type constraints, bucket policy, and CORS configuration.

### API / Lambda Failure

Possible indicators:

- Image upload succeeds
- Prediction request returns 5xx
- Lambda logs show an exception

Use the Lambda error to isolate whether the problem is S3 access, Rekognition, DynamoDB, or application logic.

### Rekognition Failure

Possible indicators:

- Lambda reaches Rekognition
- Rekognition returns an AWS service or permission error

Check IAM permissions, request format, region configuration, and service availability.

### DynamoDB Failure

Possible indicators:

- Prediction is generated
- Result persistence fails

Check the table name, write permissions, request schema, and any validation errors.

## Recovery Principles

Use the least disruptive change that fixes the confirmed failure.

- Correct configuration errors rather than recreating resources.
- Do not make the S3 bucket public.
- Do not grant broad IAM permissions as a first response.
- Make Terraform-managed infrastructure changes through the normal Terraform workflow whenever practical.
- If an emergency console change is required, reconcile Terraform afterward.

## Verification

After corrective action:

1. Open the Dog Breed Identifier page.
2. Upload a known-good dog image.
3. Confirm the S3 upload succeeds.
4. Confirm the prediction request succeeds.
5. Confirm a result is returned to the browser.
6. Confirm no new Lambda errors appear.
7. Confirm the DynamoDB result is written when expected.

If the CloudOps dashboard monitors this workload, confirm the next health check returns the workload to `healthy`.

## Incident Notes

For a meaningful outage, record:

- Detection time
- User-visible impact
- Failed component
- HTTP status or AWS error
- Root cause, if known
- Corrective action
- Verification performed
- Follow-up work required

The objective is to identify the actual failed dependency and restore the service without introducing unnecessary permissions or configuration changes.
