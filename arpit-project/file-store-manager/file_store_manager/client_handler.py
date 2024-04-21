"""
Entry point for file-store-client and handle requests
"""

from http import HTTPStatus
from typing import List

import service
from aws_lambda_powertools import Logger
from decorators import request_handler_error_responder
from eio_otel_semantic_conventions.trace import EioSpanAttributes
from evertz_io_observability.decorators import join_trace, start_span
from evertz_io_observability.otel_collector import export_trace
from file_store_client.schemas.client import (
    GET_FILE_STORE_BY_ID_PARAMETERS_SCHEMA,
    REQUEST_PAYLOAD_SCHEMA,
    RESPONSE_PAYLOAD_SCHEMA,
    GetFileStoreByIdParameters,
    MethodName,
    RequestPayload,
    ResponsePayload,
)
from file_store_client.schemas.file_store import FILE_STORE_SCHEMA, FileStore
from file_store_client.schemas.lambda_payloads import GET_BY_CLASS_PAYLOAD, GetByClassPayload
from lambda_event_sources.event_sources import EventSource
from opentelemetry.semconv.trace import SpanAttributes

logger = Logger()


@export_trace
@logger.inject_lambda_context()
@join_trace(event_source=EventSource.INVOKE)
def client_lambda(event, context):
    """
    The lambda to handle the invocation from file-store-client

    :param event: event sent from file-store-client through boto3.invoke_lmabda
    :param context: lambda execution context
    """
    logger.info(context)  # For pylint
    logger.info(event)  # For pylint

    request_payload: RequestPayload = REQUEST_PAYLOAD_SCHEMA.load(event)
    method_name = request_payload.method_name
    parameters = request_payload.parameters
    response = request_handler(method_name, parameters)  # pylint: disable=E1120
    return RESPONSE_PAYLOAD_SCHEMA.dumps(response)


@start_span()
@request_handler_error_responder
def request_handler(method_name, parameters, current_span):
    """
    Handle Get Requests from eio services
    """
    current_span.set_attributes({SpanAttributes.HTTP_METHOD: method_name})
    if method_name == MethodName.GET_FILE_STORE_BY_ID.value:
        params: GetFileStoreByIdParameters = GET_FILE_STORE_BY_ID_PARAMETERS_SCHEMA.load(parameters)
        file_store_id = str(params.file_store_id)
        tenant_id = str(params.tenant_id)
        current_span.set_attributes(
            {
                EioSpanAttributes.FILE_STORE_ID: file_store_id,
                EioSpanAttributes.TENANT_ID: tenant_id,
            }
        )

        file_store: FileStore = service.get_file_store_by_id(tenant=tenant_id, file_store_id=file_store_id)
        return ResponsePayload(status_code=HTTPStatus.OK, error_message="", body=FILE_STORE_SCHEMA.dumps(file_store))
    if method_name == MethodName.GET_FILE_STORE_BY_CLASS.value:
        params: GetByClassPayload = GET_BY_CLASS_PAYLOAD.load(parameters)
        tenant_id = str(params.tenant)
        file_class = params.class_
        current_span.set_attributes(
            {
                EioSpanAttributes.TENANT_ID: tenant_id,
                EioSpanAttributes.FILE_STORE_FILE_CLASS: file_class.name,
            }
        )

        stores: List[FileStore] = service.get_file_stores_by_file_class(tenant=tenant_id, file_class=file_class)
        return ResponsePayload(
            status_code=HTTPStatus.OK, error_message="", body=FILE_STORE_SCHEMA.dumps(stores, many=True)
        )
    return ResponsePayload(status_code=HTTPStatus.NOT_IMPLEMENTED, error_message="method_name is unknown", body="")
