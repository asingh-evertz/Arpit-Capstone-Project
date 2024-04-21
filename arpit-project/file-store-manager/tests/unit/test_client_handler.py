from http import HTTPStatus

from file_store_client.schemas.client import RESPONSE_PAYLOAD_SCHEMA, ResponsePayload
from file_store_client.schemas.file_store import FILE_STORE_SCHEMA, FileStore


def test_client_lambda_get_file_store_by_id(query_dynamodb_table, client_lambda_get_file_store_event, lambda_context):
    event = client_lambda_get_file_store_event

    from client_handler import client_lambda

    response = client_lambda(event, lambda_context)

    decoded_response_payload: ResponsePayload = RESPONSE_PAYLOAD_SCHEMA.loads(response)
    assert decoded_response_payload.error_message == ""
    assert decoded_response_payload.status_code == HTTPStatus.OK

    decoded_file_store = FILE_STORE_SCHEMA.loads(decoded_response_payload.body)
    assert isinstance(decoded_file_store, FileStore)
    assert decoded_file_store.id == client_lambda_get_file_store_event["parameters"]["file_store_id"]


def test_client_lambda_get_file_store_by_class(
    query_dynamodb_table, client_lambda_get_file_store_by_class_event, lambda_context
):
    event = client_lambda_get_file_store_by_class_event

    from client_handler import client_lambda

    response = client_lambda(event, lambda_context)

    decoded_response_payload: ResponsePayload = RESPONSE_PAYLOAD_SCHEMA.loads(response)
    assert decoded_response_payload.error_message == ""
    assert decoded_response_payload.status_code == HTTPStatus.OK

    decoded_file_stores = FILE_STORE_SCHEMA.loads(decoded_response_payload.body, many=True)
    assert isinstance(decoded_file_stores, list)
    assert len(decoded_file_stores) == 1
    assert isinstance(decoded_file_stores[0], FileStore)
