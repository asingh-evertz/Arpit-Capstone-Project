"""
Decorators
========================

The module contains set of decorators
"""

import functools
import json
import logging
from http import HTTPStatus

import errors
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from evertz_io_identity_lib.event import get_identity_from_event
from file_store_client.schemas.client import ResponsePayload
from marshmallow import ValidationError
from marshmallow_jsonapi.exceptions import IncorrectTypeError
from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import Status, StatusCode

logger = Logger()


def apigateway_error_responder(func):
    """Error handling responses"""

    # pylint: disable=R0911, R0914
    # pylint: disable=too-many-locals, too-many-statements
    @functools.wraps(func)
    def wrapper(event, _, *args, **kwargs):
        current_span = trace.get_current_span()
        identity = get_identity_from_event(event=event, verify=False)
        request_id = event.get("requestContext", {}).get("requestId")
        current_span.set_attributes({SpanAttributes.AWS_REQUEST_ID: request_id})
        try:
            response = func(event, _, current_span, identity, *args, **kwargs)
        except ClientError as err:
            logging.exception(err)
            current_span.record_exception(err, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{err}"))
            if err.response["Error"]["Code"] == "AccessDenied":
                response = {
                    "statusCode": int(err.response["ResponseMetadata"]["HTTPStatusCode"]),
                    "headers": {"Content-Type": "application/vnd.api+json"},
                    "body": json.dumps(
                        {
                            "errors": [
                                {
                                    "id": request_id,
                                    "code": str(err.response["Error"]["Code"]),
                                    "detail": "Access denied to S3 file object, check permissions.",
                                    "status": str(int(err.response["ResponseMetadata"]["HTTPStatusCode"])),
                                }
                            ]
                        }
                    ),
                }
            else:
                response = {
                    "statusCode": int(err.response["ResponseMetadata"]["HTTPStatusCode"]),
                    "headers": {"Content-Type": "application/vnd.api+json"},
                    "body": json.dumps(
                        {
                            "errors": [
                                {
                                    "id": request_id,
                                    "code": str(err.response["Error"]["Code"]),
                                    "detail": str(err),
                                    "status": str(int(err.response["ResponseMetadata"]["HTTPStatusCode"])),
                                }
                            ]
                        }
                    ),
                }
        except KeyError as key_error:
            logging.exception(key_error)
            current_span.record_exception(key_error, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{key_error}"))
            response = {
                "statusCode": 422,
                "headers": {"Content-Type": "application/vnd.api+json"},
                "body": json.dumps(
                    {
                        "errors": [
                            {
                                "id": request_id,
                                "code": "Key Error",
                                "title": "Key Error",
                                "detail": f"{key_error}",
                                "status": "422",
                            }
                        ]
                    }
                ),
            }
        except errors.ErrorBase as err:
            logging.exception(err)
            current_span.record_exception(err, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{err}"))
            response = {
                "statusCode": int(err.http_code),
                "headers": {"Content-Type": "application/vnd.api+json"},
                "body": json.dumps(
                    {
                        "errors": [
                            {
                                "id": request_id,
                                "code": str(err.code),
                                "title": err.title,
                                "detail": str(err),
                                "status": str(int(err.http_code)),
                            }
                        ]
                    }
                ),
            }
        except json.JSONDecodeError as json_decode_error:
            logging.exception(json_decode_error)
            current_span.record_exception(json_decode_error, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{json_decode_error}"))
            response = {
                "statusCode": 400,
                "headers": {"Content-Type": "application/vnd.api+json"},
                "body": json.dumps(
                    {
                        "errors": [
                            {
                                "id": request_id,
                                "code": json_decode_error.__class__.__name__,
                                "title": "Invalid JSON Error",
                                "detail": f"{json_decode_error.msg}",
                                "status": "400",
                            }
                        ]
                    }
                ),
            }

        except (ValidationError, IncorrectTypeError) as json_api_error:
            logging.exception(json_api_error)
            current_span.record_exception(json_api_error, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{json_api_error}"))
            errs = json_api_error.messages
            err_arr = errs if isinstance(errs, list) else errs.get("errors", [])
            for error in err_arr:
                error["id"] = request_id
                error["status"] = "422"
                error["title"] = "UnprocessableEntityError"

            logging.info(errs)

            response = {
                "headers": {"Content-Type": "application/vnd.api+json"},
                "statusCode": 422,
                "body": json.dumps(err_arr),
            }
        except TypeError as type_error:
            logging.exception(type_error)
            current_span.record_exception(type_error, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{type_error}"))
            response = {
                "statusCode": 422,
                "headers": {"Content-Type": "application/vnd.api+json"},
                "body": json.dumps(
                    {
                        "errors": [
                            {
                                "id": request_id,
                                "code": "Type Error",
                                "title": "Type Error",
                                "detail": f"{type_error}",
                                "status": "422",
                            }
                        ]
                    }
                ),
            }

        except ValueError as value_error:
            logging.exception(value_error)
            current_span.record_exception(value_error, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{value_error}"))
            response = {
                "statusCode": 400,
                "headers": {"Content-Type": "application/vnd.api+json"},
                "body": json.dumps(
                    {
                        "errors": [
                            {
                                "id": request_id,
                                "code": "ValueError",
                                "title": "Value Error",
                                "detail": f"{value_error}",
                                "status": "400",
                            }
                        ]
                    }
                ),
            }
        except Exception as err:
            logging.exception(err)
            current_span.record_exception(err, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{err}"))
            response = {
                "statusCode": 400,
                "headers": {"Content-Type": "application/vnd.api+json"},
                "body": json.dumps(
                    {
                        "errors": [
                            {
                                "id": request_id,
                                "code": "UnexpectedError",
                                "title": "Unexpected Error",
                                "detail": f"{err}",
                                "status": "500",
                            }
                        ]
                    }
                ),
            }
        return response

    return wrapper


def request_handler_error_responder(func):
    """Error handling responses for client handler"""

    # pylint: disable=R0911, R0914
    @functools.wraps(func)
    def wrapper(method_name, parameters, *args, **kwargs):
        current_span = trace.get_current_span()
        try:
            return func(method_name, parameters, current_span, *args, **kwargs)
        except errors.ErrorBase as err:
            logging.exception(err)
            current_span.record_exception(err, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{err}"))
            return ResponsePayload(status_code=int(err.http_code), error_message=str(err), body="")
        except ClientError as err:
            logging.exception(err)
            current_span.record_exception(err, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{err}"))
            return ResponsePayload(
                status_code=int(err.response["ResponseMetadata"]["HTTPStatusCode"]), error_message=str(err), body=""
            )
        except KeyError as err:
            logging.exception(err)
            current_span.record_exception(err, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{err}"))
            return ResponsePayload(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, error_message=str(err), body="")
        except json.JSONDecodeError as json_decode_error:
            logging.exception(json_decode_error)
            current_span.record_exception(json_decode_error, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{json_decode_error}"))
            return ResponsePayload(status_code=HTTPStatus.BAD_REQUEST, error_message=str(json_decode_error), body="")
        except TypeError as type_error:
            logging.exception(type_error)
            current_span.record_exception(type_error, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{type_error}"))
            return ResponsePayload(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, error_message=str(type_error), body="")
        except ValueError as value_error:
            logging.exception(value_error)
            current_span.record_exception(value_error, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{value_error}"))
            return ResponsePayload(status_code=HTTPStatus.BAD_REQUEST, error_message=str(value_error), body="")
        except ValidationError as err:
            logging.exception(err)
            current_span.record_exception(err, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{err}"))
            return ResponsePayload(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, error_message=str(err), body="")
        except Exception as err:
            logging.exception(err)
            current_span.record_exception(err, attributes={"error": True})
            current_span.set_status(status=Status(status_code=StatusCode.ERROR, description=f"{err}"))
            return ResponsePayload(status_code=HTTPStatus.BAD_REQUEST, error_message=str(err), body="")

    return wrapper
