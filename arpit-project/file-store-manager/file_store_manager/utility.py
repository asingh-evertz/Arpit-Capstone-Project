"""
Boto3 SNS module
====================

This module contains s3 boto client
"""

import boto3
from aws_lambda_powertools import Logger
from botocore.config import Config
from evertz_io_identity_lib.iam import restricted_table
from evertz_io_observability.decorators import start_span

# Added Boto configuration to add Retries(Exponential Backoff)
RETRY_CONFIG = Config(retries={"total_max_attempts": 4, "mode": "standard"})

sns_client = boto3.client("sns", config=RETRY_CONFIG)
"""
A low-level client representing Amazon Simple Notification System (SNS)
"""

logger = Logger()


@start_span()
def get_restricted_table_with_retry_config(table_name, tenant_id):
    """
    Get a restricted table using the tenant_id, table_name with boto3 retry configuration

    :param table_name: The name of the Table to return for the given Tenant
    :param tenant_id: The id of a tenant for which this table will be restricted
    :return: A dynamodb table resource with restricted access
    """
    return restricted_table(table_name, tenant_id, config=RETRY_CONFIG)


@start_span()
def create_sns_topic(name: str, attributes: dict = None, tags: list = None):
    """
    Creates SNS topic using boto3

    :param name: The name of the sns topic
    :param attributes: Attributes dictionary of the SNS topic
    :param tags: Tags to be added to the sns topic
    :return: Returns a dict with the TopicArn
    """
    logger.info(f"Creating sns topic with name: {name}")
    create_topic_response = sns_client.create_topic(Name=name, Attributes=attributes, Tags=tags)
    logger.debug(create_topic_response)
    return create_topic_response


@start_span()
def delete_sns_topic(topic_arn: str) -> None:
    """
    Delete sns topic and all it's subscriptions

    :param topic_arn: The arn of sns topic
    :return: None
    """
    _delete_sns_topic_subscriptions(topic_arn)
    logger.info(f"Deleting sns topic with arn [{topic_arn}]")
    sns_client.delete_topic(TopicArn=topic_arn)


def _delete_sns_topic_subscriptions(topic_arn: str) -> None:
    """
    Helper to delete sns topic subscriptions

    :param topic_arn: The arn of sns topic
    :return: None
    """
    logger.info(f"Deleting subscriptions of sns topic [{topic_arn}]")
    response = sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
    while True:
        for subscription_item in response["Subscriptions"]:
            sns_client.unsubscribe(SubscriptionArn=subscription_item["SubscriptionArn"])
        next_token = response.get("NextToken")
        if not next_token:
            break
        response = sns_client.list_subscriptions_by_topic(TopicArn=topic_arn, NextToken=next_token)
