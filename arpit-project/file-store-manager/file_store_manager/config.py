"""
Global Config
=============

Some variables have to be reused in multiple places, so we have a single reference to it in this module
"""

from os import getenv

FILE_STORE_DYNAMODB_TABLE: str = getenv("FILE_STORE_DYNAMODB_TABLE", "")
"""
Loads Configuration from environment variable;

.. envvar:: DYNAMODB_TABLE

    The DynamoDB Table for this service
"""

DEPLOYMENT_ENVIRONMENT = getenv("DEPLOYMENT_ENVIRONMENT", "prod")
"""
Loads Configuration from environment variable;

.. envvar:: DEPLOYMENT_ENVIRONMENT

    A string specifying the name of the environment we are deploying
"""

PROJECT = getenv("PROJECT", "file-store-manager")
"""
Loads Configuration from environment variable;

.. envvar:: PROJECT

    A string specifying the name of the project
"""

AWS_REGION = getenv("AWS_REGION", "")
"""
Loads Configuration from environment variable;

.. envvar:: AWS_REGION

    A string specifying the aws region
"""
