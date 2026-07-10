
import json
import os
from decimal import Decimal

import boto3


dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ["TABLE_NAME"]

table = dynamodb.Table(TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)

        return super().default(obj)


def lambda_handler(event, context):
    response = table.scan()

    items = response.get("Items", [])

    workload_statuses = [
        item
        for item in items
        if item.get("pk", "").startswith("WORKLOAD#")
        and item.get("sk") == "STATUS#LATEST"
    ]

    workload_statuses.sort(
        key=lambda item: item.get("workload_name", "")
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(
            {
                "workload_count": len(workload_statuses),
                "workloads": workload_statuses,
            },
            cls=DecimalEncoder,
        ),
    }