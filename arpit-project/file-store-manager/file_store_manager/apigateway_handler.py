"""
API Gateway Handlers
====================

This module contains functions that handle incoming invocations from API Gateway
"""

import json
from http import HTTPStatus

from aws_lambda_powertools import Logger
from decorators import apigateway_error_responder
from eio_otel_semantic_conventions.trace import EioSpanAttributes
from evertz_io_apigateway_utils.request import case_insensitive_headers
from evertz_io_apigateway_utils.response import Response, add_cors_headers, origin_header_if_subdomain
from evertz_io_observability.decorators import join_trace
from evertz_io_observability.otel_collector import export_trace
from lambda_event_sources.event_sources import EventSource
from opentelemetry.trace import Span


DEFAULT_RESPONSE_CONTENT_TYPE = "application/vnd.api+json"
BODY = "body"

logger = Logger()


# pylint: disable=E1135
@export_trace
@logger.inject_lambda_context()
@join_trace(event_source=EventSource.API_GATEWAY_REQUEST)
@add_cors_headers(origin=origin_header_if_subdomain, credentials=True)
@case_insensitive_headers
@apigateway_error_responder
def hello_world(event, _, current_span: Span, identity):
    """
    Get Hello World

    :param event: event with data to process
    :param _: lambda execution context
    :param current_span: current span context
    :param identity: identity of the user making the request
    :return: FileStore
    """
    logger.debug(event)

    tenant_id = identity.tenant
    logger.append_keys(tenent_id=tenant_id, user_id=identity.sub)
    current_span.set_attributes(
        {
            EioSpanAttributes.TENANT_ID: tenant_id,
            EioSpanAttributes.USER_ID: identity.sub,
            EioSpanAttributes.USER_NAME: identity.username,
        }
    )

    logger.info("Invoking Hello world Lambda for Capstone Project")

    response = Response(
        status_code=HTTPStatus.OK,
        body={"msg": "Hello World"},
        content_type=DEFAULT_RESPONSE_CONTENT_TYPE,
        serializer=json.dumps,
    )
    logger.debug(response)
    return response.dump()
