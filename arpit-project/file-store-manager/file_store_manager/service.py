"""
File-store Manager Service
-------------------

This module contains functions with service logic
"""

import datetime
import json
from typing import List
from uuid import uuid4

import db
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from config import PROJECT
from eio_otel_semantic_conventions.trace import EioSpanAttributes
from errors import FilestoreNameAlreadyExists, FileStorePatchError, ForbiddenAccess
from evertz_io_events import EventBridge
from evertz_io_identity_lib import Identity
from evertz_io_observability.decorators import start_span
from file_store_client.schemas.file_class import FileClass
from file_store_client.schemas.file_store import FileStore
from file_store_client.schemas.file_store_state import FileStoreState
from file_store_client.schemas.modification_info import ModificationInfo
from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes
from schema.events import FileStoreCreated, FileStoreCreatedData
from user_management_client.client import get_groups_for_user
from utility import create_sns_topic, delete_sns_topic

logger = Logger()


def _create_topic(file_store: FileStore):
    """
    Create a new SNS topic for the given file store

    :param file_store: A new FileStore
    """
    logger.info(f"Creating topic for file-store : {file_store} started")
    sns_policy = json.dumps(
        {
            "Statement": {
                "Sid": "publish-from-s3",
                "Effect": "Allow",
                "Resource": "arn:aws:sns:*:*:*",
                "Principal": {"Service": "s3.amazonaws.com"},
                "Action": "SNS:Publish",
                "Condition": {"ArnLike": {"aws:SourceArn": "arn:aws:s3:*:*:" + file_store.bucket}},
            }
        }
    )
    attributes = {"Policy": sns_policy}
    sns_tags = [
        {"Key": "project", "Value": PROJECT},
        {"Key": "file_store_id", "Value": file_store.id},
        {"Key": "tenant_id", "Value": file_store.tenant},
        {"Key": "class", "Value": file_store.store_type.file_class.name},
    ]
    sns_name = PROJECT + "-" + file_store.id

    create_topic_response = create_sns_topic(name=sns_name, attributes=attributes, tags=sns_tags)

    topic_arn = create_topic_response["TopicArn"]
    logger.info(f"ARN of the created topic : [{topic_arn}]")
    file_store.topic_arn = topic_arn


@start_span()
def _emit_filestore_event(file_store: FileStore):
    """
    puts file-store data in event bridge

     :param file_store: FileStore
    """
    # Emit to event bridge
    event_data = FileStoreCreatedData(
        identity="",
        correlation_id="",
        tenant_id=file_store.tenant,
        sns_arn=file_store.topic_arn,
        file_class=file_store.store_type.file_class,
    )
    event = FileStoreCreated(source=PROJECT, data=event_data)
    EventBridge().emit(event)


@start_span()
def create_file_store(identity: Identity, new_file_store: FileStore) -> FileStore:
    """
    Create a new FileStore

    Given a new FileStore, add server side fields and save it to a Database

    - Generates a unique ``id`` for this FileStore
    - Adds the ``created`` datetime to this FileStore

    :param identity: The caller Identity
    :param new_file_store: A new FileStore
    :return: The saved new FileStore
    """
    created = datetime.datetime.now()

    new_file_store.id = str(uuid4())
    tenant_id = identity.tenant

    new_file_store.tenant = tenant_id
    current_span = trace.get_current_span()
    store_type = new_file_store.store_type
    current_span.set_attributes(
        {
            EioSpanAttributes.FILE_STORE_ID: new_file_store.id,
            SpanAttributes.AWS_S3_BUCKET: new_file_store.bucket,
            EioSpanAttributes.FILE_STORE_FILE_CLASS: store_type.file_class.name,
            EioSpanAttributes.FILE_STORE_FILE_FORMATS: [file_format.name for file_format in store_type.file_formats],
        }
    )
    check_file_store_name_already_exists(tenant_id=tenant_id, new_file_store=new_file_store)
    new_file_store.modification_info = ModificationInfo.create_modification_info(
        created=created, last_modified=created, created_by=identity.sub, last_modified_by=identity.sub
    )
    new_file_store.state = FileStoreState.DEPLOYMENT_PENDING
    if new_file_store.store_type.file_class.incoming is True:
        _create_topic(new_file_store)
    _emit_filestore_event(new_file_store)
    db.put_file_store(file_store=new_file_store)
    return new_file_store


def _update_file_store(existing_file_store: FileStore, file_store: FileStore, last_modified_by: str):
    existing_file_store.bucket = file_store.bucket
    existing_file_store.folder_prefix = file_store.folder_prefix
    existing_file_store.store_type.file_formats = file_store.store_type.file_formats
    existing_file_store.access_role_arn = file_store.access_role_arn
    existing_file_store.modification_info.last_modified_by = last_modified_by
    existing_file_store.modification_info.last_modified = datetime.datetime.now()
    existing_file_store.metadata = file_store.metadata
    if file_store.description is not None:
        existing_file_store.description = file_store.description
    if file_store.writeable is not None:
        existing_file_store.writeable = file_store.writeable
    if existing_file_store.name != file_store.name:
        check_file_store_name_already_exists(tenant_id=existing_file_store.tenant, new_file_store=file_store)
        existing_file_store.name = file_store.name
    if existing_file_store.state in [FileStoreState.ACTIVE, FileStoreState.ERROR, FileStoreState.DEPLOYMENT_PENDING]:
        existing_file_store.state = FileStoreState.DEPLOYMENT_PENDING
    else:
        existing_file_store.state = FileStoreState.UNKNOWN
    return existing_file_store


@start_span()
def update_file_store(
    tenant_id: str, new_file_store: FileStore, file_store_id: str, last_modified_by: str
) -> FileStore:
    """
    Patch the given file store

    :param tenant_id: The Tenant Id
    :param new_file_store: The File store Object
    :param last_modified_by: Modified by user
    :param file_store_id: File store Id

    :return: File store object
    """

    logger.info(f"Updating file store [{file_store_id}]...")
    existing_file_store = get_file_store_by_id(file_store_id=file_store_id, tenant=tenant_id)
    if existing_file_store.store_type.file_class != new_file_store.store_type.file_class:
        raise FileStorePatchError(
            f"Updating the file class [{existing_file_store.store_type.file_class}] with a new file class"
            f" [{new_file_store.store_type.file_class}] is not allowed"
        )

    updated_file_store = _update_file_store(existing_file_store, new_file_store, last_modified_by)
    current_span = trace.get_current_span()
    store_type = updated_file_store.store_type
    current_span.set_attributes(
        {
            EioSpanAttributes.FILE_STORE_ID: updated_file_store.id,
            SpanAttributes.AWS_S3_BUCKET: updated_file_store.bucket,
            EioSpanAttributes.FILE_STORE_FILE_FORMATS: [file_format.name for file_format in store_type.file_formats],
        }
    )
    db.patch_file_store(updated_file_store)
    return updated_file_store


@start_span()
def check_file_store_name_already_exists(tenant_id: str, new_file_store: FileStore):
    """
    Checking whether file store name is unique or not
    """
    file_store_list = get_all_files_stores_by_tenant(tenant_id=tenant_id)
    for file_store in file_store_list:
        if file_store.name == new_file_store.name:
            raise FilestoreNameAlreadyExists(new_file_store.name)


@start_span()
def get_file_store_by_id(tenant: str, file_store_id: str) -> FileStore:
    """
    Get a FileStore by tenant id and file store id
    """
    return db.get_file_store_by_id(tenant, file_store_id)


@start_span()
def get_file_stores_by_file_class(tenant: str, file_class: FileClass) -> List[FileStore]:
    """
    Get a FileStore by tenant id and store type
    """
    return db.get_file_stores_by_file_class(tenant, file_class)


@start_span()
def get_all_files_stores_by_tenant(tenant_id: str):
    """
    Get all FileStores for a tenant id.
    """
    return db.get_file_stores_by_tenant(tenant_id=tenant_id)


@start_span()
def get_file_stores_by_tenant_and_bucket_name(tenant_id: str, bucket_name: str) -> List[FileStore]:
    """
    Get all Sibling FileStores for a tenant id with similar bucket name.
    """
    return db.get_file_stores_by_tenant_and_bucket_name(tenant_id=tenant_id, bucket_name=bucket_name)


@start_span()
def delete_file_store_by_id(tenant: str, file_store_id: str) -> None:
    """
    Delete a FileStore by file_store_id
    Also deletes the sns topic associated with the file store

    :param tenant: The tenant id
    :param file_store_id: The file store id to delete
    :returns: None
    """
    file_store: FileStore = db.get_file_store_by_id(tenant, file_store_id)
    if file_store.store_type.file_class.incoming is True or file_store.topic_arn is not None:
        try:
            delete_sns_topic(file_store.topic_arn)
        except ClientError as client_error:
            if client_error.response["Error"]["Code"] == "InternalErrorException":
                raise
            logger.warning(f"Deletion of topic [{file_store.topic_arn}] unsuccessful. Error [{client_error}]")
    db.delete_file_store_by_id(tenant, file_store_id)


@start_span()
def check_if_admin(tenant_id: str, user_id: str) -> None:
    """
    Check if user is part of admin group for tenant
    :param tenant_id: tenant of caller
    :param user_id: user id (sub) of caller
    :raises: Forbidden Access
    :return: None
    """
    logger.info(f"Validate if user [{user_id}] has permission to make the API call")
    user_groups = get_groups_for_user(user_id=user_id, tenant_id=tenant_id)

    if "admin" not in user_groups:
        logger.exception(f"User [{user_id}] does not have admin access right. Please contact administrator")
        raise ForbiddenAccess()
