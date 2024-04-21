"""
The module contains code to work with DynamoDB

-------------------------------------
Database Structure

Key Attributes:
--------------------------
store-id: str
tenant-id: str
class: str

Keys
--------------------------
primary-key: (hash: tenant-id, range: channel-id)

Indexes
--------------------------
LSI-1: (hash: tenant-id, range: class)

"""

from typing import List

from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from config import FILE_STORE_DYNAMODB_TABLE
from errors import BucketNameNotFound, FileStoreConflict, FileStoreNotFound
from evertz_io_observability.decorators import start_span
from file_store_client.schemas.file_class import FileClass
from file_store_client.schemas.file_store import FILE_STORE_DB_SCHEMA, FILE_STORE_SCHEMA, FileStore
from utility import get_restricted_table_with_retry_config

logger = Logger()

# Unique Attributes
TENANT_ID = "tenant-id"
CLASS = "class"
STORE_ID = "store-id"

DATA = "data"


@start_span()
def put_file_store(file_store: FileStore) -> None:
    """
    Store a file_store

    :param file_store: FileStore to store
    :raises FileStoreConflict: When a FileStore already exists with the same `id`
    """

    logger.info(f"Writing FileStore [{file_store.id}]")

    tenant_id = str(file_store.tenant)

    file_class = file_store.store_type.file_class

    item = {
        CLASS: file_class.name,
        TENANT_ID: tenant_id,
        STORE_ID: str(file_store.id),
        DATA: FILE_STORE_SCHEMA.dump(file_store),
    }

    # Fail if the (tenant_id, store_id) pair already exists
    cond = Attr(TENANT_ID).not_exists() & Attr(STORE_ID).not_exists()

    if not file_class.many:
        # Check if tenant already has this type of file store
        file_stores = get_file_stores_by_file_class(tenant_id, file_class, limit=1)
        if len(file_stores) > 0:
            logger.error(
                f"Unable to save file store: there is already one file store of the class [{file_class.name}] and only"
                " one is supported"
            )
            raise FileStoreConflict(file_class.name)

    kwargs = {"Item": item, "ConditionExpression": cond}

    table = get_restricted_table_with_retry_config(FILE_STORE_DYNAMODB_TABLE, tenant_id)

    try:
        response = table.put_item(**kwargs)
        logger.debug(f"Table put response:[{response}]")
        logger.info("Writing filestore to the db successful")
    except ClientError as client_error:
        error = client_error.response.get("Error", {})
        error_code = error.get("Code", "?")
        logger.error(f"Error Code: [{error_code}]")

        if error_code == "ConditionalCheckFailedException":
            logger.exception("FileStore already exists")
            raise FileStoreConflict(file_store.id) from client_error
        raise


@start_span()
def patch_file_store(file_store: FileStore) -> None:
    """
    Update a file_store

    :param file_store: FileStore to update
    :raises FileStoreConflict: When a FileStore already exists with the same `id`
    """

    logger.info(f"Updating FileStore [{file_store.id}]")
    tenant_id = str(file_store.tenant)
    file_store_id = file_store.id

    try:
        table = get_restricted_table_with_retry_config(FILE_STORE_DYNAMODB_TABLE, tenant_id)
        response = table.update_item(
            Key={"tenant-id": tenant_id, "store-id": file_store_id},
            UpdateExpression="SET #data=:file_store",
            ExpressionAttributeNames={"#data": "data"},
            ExpressionAttributeValues={":file_store": FILE_STORE_SCHEMA.dump(file_store)},
        )
        logger.debug(f"Response:  [{response}]")
        logger.info("Modified file store successfully.")
    except ClientError as client_error:
        error = client_error.response.get("Error", {})
        error_code = error.get("Code", "")
        logger.exception(f"Failed to update file store with [{file_store_id}] with [{error_code}]")
        raise


@start_span()
def get_file_stores_by_file_class(tenant_id: str, file_class: FileClass, limit=None) -> List[FileStore]:
    """
    Retrieve a FileStore by tenant id and FileClass type
    """
    kwargs = {}
    if limit:
        kwargs["Limit"] = limit

    table = get_restricted_table_with_retry_config(FILE_STORE_DYNAMODB_TABLE, tenant_id)
    cond = Key(TENANT_ID).eq(tenant_id) & Key(CLASS).eq(file_class.name)
    response = table.query(IndexName="LSI-1", KeyConditionExpression=cond, **kwargs)

    return FILE_STORE_DB_SCHEMA.load([item[DATA] for item in response["Items"]], many=True)


@start_span()
def get_file_store_by_id(tenant_id: str, file_store_id: str) -> FileStore:
    """
    Retrieve a FileStore by tenant id and file store id
    :throws: FileStoreNotFound if the FileStore doesn't exist
    :throws: Reraises errors from the GetItem operation
    """
    table = get_restricted_table_with_retry_config(FILE_STORE_DYNAMODB_TABLE, tenant_id)
    kwargs = {"Key": {TENANT_ID: tenant_id, STORE_ID: file_store_id}}
    try:
        response = table.get_item(**kwargs)
        logger.debug(f"Db response from get_item query: [{response}]")
    except ClientError as client_error:
        error = client_error.response.get("Error", {})
        error_code = error.get("Code", "?")
        logger.error(f"Error Code: [{error_code}]")
        raise

    if "Item" not in response:
        raise FileStoreNotFound

    item = response.get("Item")
    return FILE_STORE_DB_SCHEMA.load(item[DATA])


@start_span()
def delete_file_store_by_id(tenant_id: str, file_store_id: str) -> None:
    """
    Delete a FileStore by file store id

    :param tenant_id: The tenant Id
    :param file_store_id: The file store id to delete
    :returns: None
    """
    logger.info(f"Deleting FileStore [{file_store_id}] Tenant [{tenant_id}]")
    table = get_restricted_table_with_retry_config(FILE_STORE_DYNAMODB_TABLE, tenant_id)
    kwargs = {"Key": {TENANT_ID: tenant_id, STORE_ID: file_store_id}}
    table.delete_item(**kwargs)


@start_span()
def get_file_stores_by_tenant(tenant_id: str) -> List[FileStore]:
    """
    Get all FileStores for a tenant
    :throws: Reraises errors from the Query operation
    """
    table = get_restricted_table_with_retry_config(FILE_STORE_DYNAMODB_TABLE, tenant_id)
    cond = Key(TENANT_ID).eq(tenant_id)

    try:
        response = table.query(KeyConditionExpression=cond)
    except ClientError as client_error:
        error = client_error.response.get("Error", {})
        error_code = error.get("Code", "?")
        logger.error(f"Error Code: [{error_code}]")
        raise

    items = [item[DATA] for item in response.get("Items")]
    return FILE_STORE_DB_SCHEMA.load(items, many=True)


@start_span()
def get_file_stores_by_tenant_and_bucket_name(tenant_id: str, bucket_name: str) -> List[FileStore]:
    """
    Get all FileStores for a tenant with similar bucket name
    :throws: Reraises errors from the Query operation
    """
    logger.info(f"Retrieving file stores with similar bucket name [{bucket_name}] for tenant [{tenant_id}]")
    table = get_restricted_table_with_retry_config(FILE_STORE_DYNAMODB_TABLE, tenant_id)
    cond = Key(TENANT_ID).eq(tenant_id)

    try:
        response = table.query(KeyConditionExpression=cond)
    except ClientError as client_error:
        error = client_error.response.get("Error", {})
        error_code = error.get("Code", "?")
        logger.error(f"Error Code: [{error_code}]")
        raise

    items = [item[DATA] for item in response.get("Items") if item[DATA]["bucket"] == bucket_name]
    if not items:
        raise BucketNameNotFound(bucket_name)
    logger.info(f"Successfully retrieved FileStores with bucket name [{bucket_name}] for tenant [{tenant_id}]: {items}")
    return FILE_STORE_DB_SCHEMA.load(items, many=True)
