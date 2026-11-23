from __future__ import annotations

import logging
import os

import boto3

logger = logging.getLogger(__name__)


def emit_daily_spend_gbp(total_gbp: float) -> None:
    try:
        cw = boto3.client("cloudwatch", region_name=os.environ.get("AWS_REGION", "eu-west-2"))
        cw.put_metric_data(
            Namespace="RagPlatform",
            MetricData=[
                {
                    "MetricName": "DailySpendGBP",
                    "Value": total_gbp,
                    "Unit": "None",
                }
            ],
        )
    except Exception:
        logger.exception("CloudWatch metric emit failed")