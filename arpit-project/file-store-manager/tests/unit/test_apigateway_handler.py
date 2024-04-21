import json
from http import HTTPStatus
from unittest import mock
from unittest.mock import patch

import pytest
from apigateway_handler import (
    add_file_store,
    get_file_stores_by_bucket,
    handle_get_file_store,
    handle_get_file_stores_by_type,
    patch_file_store,
    remove_file_store,
)
from file_store_client.schemas.file_class import FileClass
from moto import mock_events, mock_sns
from unit.conftest import (
    CREATED_USER,
    TENANT_TOKEN,
    add_file_store_payload,
    add_file_store_payload_with_metadata,
    file_store_data_2,
)


class TestAPIGateway:
    @pytest.mark.parametrize(
        "store_type",
        [
            FileClass.PLAYLIST_IMPORT,
            FileClass.CONTENT_SERVICE_ASSET,
            FileClass.CONTENT_SERVICE_TIMELINE,
            FileClass.ASRUN,
            FileClass.PLAYLIST_EXPORT,
        ],
    )
    @mock.patch("service.get_groups_for_user", return_value=["admin"])
    @mock_sns
    def test_handler_add_file_store_manager(
        self, _, store_type, empty_dynamodb_table, get_caller_identity, lambda_context
    ):
        payload = add_file_store_payload(store_type.value, ["pxf", "xml"])

        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": payload,
            },
            lambda_context,
        )

        with patch("service.EventBridge.emit") as mock_emit:
            create_response = add_file_store(event, context)
            mock_emit.assert_called_once()
            event_data = mock_emit.call_args[0][0].data
            assert event_data.file_class == store_type

            assert create_response["statusCode"] == HTTPStatus.OK

        # Validate Response Headers
        assert "Content-Type" in create_response["headers"]
        assert create_response["headers"]["Content-Type"] == "application/vnd.api+json"

        # Validate Response Body
        body = json.loads(create_response["body"])
        body_attributes = body["data"]["attributes"]
        assert len(body["data"]["id"]) > 10
        assert body_attributes["bucket"] == "testcustomerpxfbucket"
        assert body_attributes["storeType"]["fileClass"] == store_type.value
        assert body_attributes["accessRoleArn"] == "arn:aws:iam::00000:role/abc"
        if store_type not in [FileClass.ASRUN, FileClass.PLAYLIST_EXPORT]:
            assert len(body_attributes["topicArn"]) > 10

    @mock.patch("service.get_groups_for_user", return_value=["user"])
    def test_add_file_store_when_not_an_admin(self, _, get_caller_identity, lambda_context):
        payload = add_file_store_payload(FileClass.ASRUN.value, ["pxf", "xml"])

        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": payload,
            },
            lambda_context,
        )
        create_response = add_file_store(event, context)
        assert create_response["statusCode"] == HTTPStatus.FORBIDDEN
        response_body = json.loads(create_response["body"])
        assert response_body["errors"][0]["code"] == "ForbiddenAccess"

    @mock.patch("service.get_groups_for_user", return_value=["admin"])
    @mock_sns
    def test_add_file_store_for_data_translation(self, _, empty_dynamodb_table, get_caller_identity, lambda_context):
        payload = add_file_store_payload_with_metadata(FileClass.DATA_TRANSLATION.value, ["xml"])

        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": payload,
            },
            lambda_context,
        )

        with patch("service.EventBridge.emit") as mock_emit:
            create_response = add_file_store(event, context)
            mock_emit.assert_called_once()
            event_data = mock_emit.call_args[0][0].data
            assert event_data.file_class == FileClass.DATA_TRANSLATION

            assert create_response["statusCode"] == HTTPStatus.OK

        # Validate Response Headers
        assert "Content-Type" in create_response["headers"]
        assert create_response["headers"]["Content-Type"] == "application/vnd.api+json"

        # Validate Response Body
        body = json.loads(create_response["body"])
        body_attributes = body["data"]["attributes"]
        assert len(body["data"]["id"]) > 10
        assert body_attributes["bucket"] == "testcustomerpxfbucket"
        assert body_attributes["storeType"]["fileClass"] == FileClass.DATA_TRANSLATION.value
        assert body_attributes["accessRoleArn"] == "arn:aws:iam::00000:role/abc"
        assert len(body_attributes["topicArn"]) > 10

    @mock.patch("service.get_groups_for_user", return_value=["admin"])
    @mock_sns
    def test_handler_add_file_store_manager_wrong_metadata_config(
        self, _, empty_dynamodb_table, get_caller_identity, lambda_context
    ):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": json.dumps(file_store_data_2),
            },
            lambda_context,
        )
        create_response = add_file_store(event, context)
        assert create_response["statusCode"] == 422
        body = json.loads(create_response["body"])
        assert body[0]["detail"] == "Metadata can only be configured to a file store with DATA_TRANSLATION class"

    @mock_events
    def test_handler_get_file_store(self, query_dynamodb_table, lambda_context):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {"id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )

        query_response = handle_get_file_store(event, context)
        assert query_response["statusCode"] == HTTPStatus.OK
        body = json.loads(query_response["body"])
        file_store_body = body["data"]["attributes"]
        assert file_store_body["bucket"] == "testcustomerpxfbucket"
        assert file_store_body["storeType"]["fileClass"] == FileClass.PLAYLIST_IMPORT.value
        assert file_store_body["modificationInfo"] is not None
        assert file_store_body["modificationInfo"]["createdBy"] == CREATED_USER

    @mock_events
    def test_handler_get_file_store_wrong_metadata_config(
        self, query_dynamodb_table_for_all_files_stores, lambda_context
    ):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {"id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467b"},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )

        query_response = handle_get_file_store(event, context)
        assert query_response["statusCode"] == HTTPStatus.OK
        body = json.loads(query_response["body"])
        file_store_body = body["data"]["attributes"]
        assert file_store_body["bucket"] == "testcustomerpxfbucket"
        assert file_store_body["storeType"]["fileClass"] == FileClass.PLAYLIST_EXPORT.value
        assert file_store_body["modificationInfo"] is not None
        assert file_store_body["modificationInfo"]["createdBy"] == CREATED_USER

    @mock.patch("service.get_groups_for_user", return_value=["admin"])
    @mock_events
    def test_handler_patch_file_store(self, _, query_dynamodb_table, lambda_context):
        payload = add_file_store_payload(FileClass.PLAYLIST_IMPORT.value, ["pxf", "xml"])

        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {"id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": payload,
            },
            lambda_context,
        )

        patch_response = patch_file_store(event, context)
        assert patch_response["statusCode"] == HTTPStatus.OK
        assert "Content-Type" in patch_response["headers"]
        assert patch_response["headers"]["Content-Type"] == "application/vnd.api+json"

        # Validate Response Body
        body = json.loads(patch_response["body"])
        body_attributes = body["data"]["attributes"]
        assert len(body["data"]["id"]) > 10
        assert body_attributes["bucket"] == "testcustomerpxfbucket"
        assert body_attributes["storeType"]["fileFormats"] == ["pxf", "xml"]

    @mock.patch("service.get_groups_for_user", return_value=["user"])
    def test_patch_file_store_when_not_an_admin(self, _, lambda_context):
        payload = add_file_store_payload(FileClass.PLAYLIST_IMPORT.value, ["pxf", "xml"])

        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {"id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": payload,
            },
            lambda_context,
        )
        patch_response = patch_file_store(event, context)
        assert patch_response["statusCode"] == HTTPStatus.FORBIDDEN
        response_body = json.loads(patch_response["body"])
        assert response_body["errors"][0]["code"] == "ForbiddenAccess"

    @mock.patch("service.get_groups_for_user", return_value=["admin"])
    @mock_events
    def test_handler_patch_file_store_with_different_file_class(self, _, query_dynamodb_table, lambda_context):
        payload = add_file_store_payload(FileClass.PLAYLIST_EXPORT.value, ["pxf", "xml"])

        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "pathParameters": {"id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"},
                "queryStringParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": payload,
            },
            lambda_context,
        )
        patch_response = patch_file_store(event, context)
        assert patch_response["statusCode"] == HTTPStatus.BAD_REQUEST

    def test_handler_get_all_file_stores(self, query_dynamodb_table_for_all_files_stores, lambda_context):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "queryStringParameters": {},
                "pathParameters": {},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )

        from apigateway_handler import handle_get_file_store

        query_response = handle_get_file_store(event, context)
        assert query_response["statusCode"] == HTTPStatus.OK
        body = json.loads(query_response["body"])
        file_store_body = body["data"]
        assert len(file_store_body) == 2
        assert file_store_body[0]["id"] == "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"
        assert file_store_body[0]["attributes"]["storeType"]["fileClass"] == FileClass.PLAYLIST_IMPORT.value
        assert file_store_body[0]["attributes"]["modificationInfo"] is not None
        assert file_store_body[0]["attributes"]["modificationInfo"]["createdBy"] == CREATED_USER
        assert file_store_body[1]["id"] == "52bbcefc-df71-42c8-9ad3-a87c3ac4467b"
        assert file_store_body[1]["attributes"]["storeType"]["fileClass"] == FileClass.PLAYLIST_EXPORT.value
        assert file_store_body[1]["attributes"]["modificationInfo"] is not None
        assert file_store_body[1]["attributes"]["modificationInfo"]["createdBy"] == CREATED_USER
        for file_store in file_store_body:
            file_store_object = file_store["attributes"]
            assert file_store_object["bucket"] == "testcustomerpxfbucket"

    @mock.patch("service.get_groups_for_user", return_value=["admin"])
    def test_handler_remove_file_store_file_class_incoming_true(
        self, _, query_dynamodb_table_for_all_files_stores, create_mock_sns, lambda_context
    ):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "queryStringParameters": {},
                "pathParameters": {"id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )

        query_response = remove_file_store(event, context)

        assert query_response["statusCode"] == HTTPStatus.NO_CONTENT
        # Assert that the sns and its subscription created by the pytest fixture are deleted
        sns_client = create_mock_sns
        list_topic_response = sns_client.list_topics()
        assert len(list_topic_response["Topics"]) == 0

        list_subscriptions_response = sns_client.list_subscriptions()
        assert len(list_subscriptions_response["Subscriptions"]) == 0

    @mock.patch("service.get_groups_for_user", return_value=["user"])
    def test_remove_file_store_when_not_an_admin(self, _, lambda_context):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "queryStringParameters": {},
                "pathParameters": {"id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )

        query_response = remove_file_store(event, context)
        assert query_response["statusCode"] == HTTPStatus.FORBIDDEN
        response_body = json.loads(query_response["body"])
        assert response_body["errors"][0]["code"] == "ForbiddenAccess"

    @mock.patch("service.get_groups_for_user", return_value=["admin"])
    def test_handler_remove_file_store_file_class_incoming_false(
        self, _, query_dynamodb_table_for_all_files_stores, create_mock_sns, lambda_context
    ):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "queryStringParameters": {},
                "pathParameters": {"id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467b"},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )

        query_response = remove_file_store(event, context)

        assert query_response["statusCode"] == HTTPStatus.NO_CONTENT
        # Assert that the sns and its subscription created by the pytest fixture are not deleted
        sns_client = create_mock_sns
        list_topic_response = sns_client.list_topics()
        assert len(list_topic_response["Topics"]) == 1

        list_subscriptions_response = sns_client.list_subscriptions()
        assert len(list_subscriptions_response["Subscriptions"]) == 1

    def test_handler_get_file_stores_by_type(self, query_dynamodb_table, lambda_context):
        # Retrieve single CONTENT_SERVICE_ASSET type store in db
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "queryStringParameters": {},
                "pathParameters": {"fileClass": "playlist-import"},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )
        query_response = handle_get_file_stores_by_type(event, context)

        assert query_response["statusCode"] == HTTPStatus.OK
        body = json.loads(query_response["body"])
        file_store_body = body["data"]
        assert len(file_store_body) == 1

        file_store = file_store_body[0]
        assert file_store["id"] == "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"

        file_store_object = file_store["attributes"]
        assert file_store_object["storeType"]["fileClass"] == FileClass.PLAYLIST_IMPORT.value
        assert file_store_object["bucket"] == "testcustomerpxfbucket"

    def test_handle_get_file_stores_by_type_invalid(self, query_dynamodb_table, lambda_context):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "queryStringParameters": {},
                "pathParameters": {"fileClass": "INVALID_FILE_CLASS"},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )
        query_response = handle_get_file_stores_by_type(event, context)

        assert query_response["statusCode"] == HTTPStatus.BAD_REQUEST
        body = json.loads(query_response["body"])
        assert body["errors"][0]["detail"] == "File Store type [INVALID_FILE_CLASS] is not a valid FileClass"

    def test_get_file_stores_by_bucket(self, query_dynamodb_table, lambda_context):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "queryStringParameters": {},
                "pathParameters": {"bucketName": "testcustomerpxfbucket"},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": add_file_store_payload,
            },
            lambda_context,
        )
        query_response = get_file_stores_by_bucket(event, context)
        assert query_response["statusCode"] == HTTPStatus.OK
        body = json.loads(query_response["body"])
        file_store_body = body["data"]
        assert len(file_store_body) == 1

        file_store = file_store_body[0]
        assert file_store["id"] == "52bbcefc-df71-42c8-9ad3-a87c3ac4467a"

        file_store_object = file_store["attributes"]
        assert file_store_object["bucket"] == "testcustomerpxfbucket"

    def test_get_file_stores_by_bucket_invalid(self, query_dynamodb_table, lambda_context):
        event, context = (
            {
                "requestContext": {"apiId": "abc123"},
                "queryStringParameters": {},
                "pathParameters": {"bucketName": "Invalid_Bucket_Name"},
                "headers": {"Authorization": TENANT_TOKEN},
                "body": {},
            },
            lambda_context,
        )
        query_response = get_file_stores_by_bucket(event, context)
        assert query_response["statusCode"] == 400
        body = json.loads(query_response["body"])
        assert body["errors"][0]["detail"] == "Bucket Invalid_Bucket_Name not found"
