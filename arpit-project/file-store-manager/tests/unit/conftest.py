import json
import os

import boto3
import config
import moto
import pytest
from evertz_io_identity_lib import Identity
from file_store_client.schemas.file_class import FileClass
from file_store_client.schemas.file_store import FILE_STORE_DB_SCHEMA, FILE_STORE_JSONAPI, FILE_STORE_SCHEMA, FileStore
from moto import mock_sns, mock_sts

EVERTZ_TOKEN = (
    "eyJraWQiOiJmQzVGdTM3VDh1R3hUVEhCRndiQzR6UVRmRHFLNTlKYXkyTlhzaXFwV0l3PSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJmNGRi"
    "OTNjYy02OWQ2LTQyZjgtOWNlNy04OTU3NzZmMTc3ZjUiLCJhdWQiOiIzbmJpcmo0Y2JkMm5ja2tjaTA2cnA5Mzk5NCIsImV2ZW50X2lkIjoi"
    "ZTU4NmFhMDMtNzdlMy0xMWU5LWEyZGYtZmI0ODg5N2U5ZjNlIiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1NTgwMTU2MzAsImlz"
    "cyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTEuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0xX3h1V2xrc2J4diIsImNvZ25pdG86"
    "dXNlcm5hbWUiOiJyb290IiwiY3VzdG9tOnRlbmFudF9pZCI6IjAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAwMCIsImV4cCI6"
    "MTU1ODAxOTIzMCwiaWF0IjoxNTU4MDE1NjMwLCJlbWFpbCI6ImdhbHRvbkBldmVydHouY29tIn0.GRxHORoUdMP6vp43rxPMWLivcm-TRd2F"
    "5ir1EjdVHiqmYU2WLphe5TBbfYae9QkiGOZJ1Nv2ZD53W5w9SAKLjP3L6aioqUIcVgWJ9cv-7hKFWAqZrnS4Ionn_pXxGd-6dDo6p3TAu9ph"
    "TY0kP7Br8HMsv-wtL3dxLzmx80RYoKiJYzkCJxLPsd3L9VoKhAIpBEllYlktUXkwW9I_69uM_e03y4sHFdGbv9MKpVRoQ9JO6xri7hy_B9Jl"
    "nK79SyndXEd0Beo9ufHmCnv2q1W72Te3tZF9rQLU456pFlW6sQaOsAqQJZzraXv_9jSIbExmiT269ErRL__RAfBFe_3q6A"
)
TENANT_ID = "85d11709-7b87-4eef-8c80-6a670810dfe0"
TENANT_TOKEN = (
    "eyJraWQiOiJGXC80WUd2T2RkUmV6Y0crUWp6R2FBR2E2OWVTem1UUjNnalg0enhmWlVqbz0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI5NDh"
    "kMmM5ZS0zNjExLTQ5NDMtYTMyMS04YWE2OTM5NWNiODUiLCJhdWQiOiI0MzNrMDhlbXR2cDZicTI0Y3FhZ2wyNjNiaCIsImV2ZW50X2lkIjo"
    "iYjAzYjg4MDItYzY2OC0xMWU4LThjOGYtYTE2MzUzODI0NmIzIiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE1Mzg1MDEzNTcsIml"
    "zcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTEuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0xXzFNZzBjVHkzMSIsImNvZ25pdG8"
    "6dXNlcm5hbWUiOiJyb290IiwiY3VzdG9tOnRlbmFudF9pZCI6Ijg1ZDExNzA5LTdiODctNGVlZi04YzgwLTZhNjcwODEwZGZlMCIsImV4cCI"
    "6MTUzODUwNDk1NywiaWF0IjoxNTM4NTAxMzU3LCJlbWFpbCI6ImdhbHRvbkBldmVydHouY29tIn0.YNE2ZZGOZLrWsf8Ib9zRS9emVnBEuqa"
    "WM8EcFRhX4_rwmAcJB7IDEpTKkpJVLU90NlPe13BUG-okARnHly4qNMEoeDunPjgIqHulUXz4awy3h3Xb7Fr0sQ9T6KJZpvufJDFt9xEJoag"
    "JACeTZambzTcp7Qdgr-mmOXbZnVHt5mxeTHOHYBuWOLDcSDfxFrEgNOTfacbskx9OM996G2SoM0LaJLm_qI-i8bJ0tRWeBWuE5gG5YRBZ1n0"
    "dgh73OStdQyfzjd746LegDPXThgKgOS6mId-T0M5cAx_ULrQvJ8NrglMeUztieKQotM60ni5Sd133vv29ccNpFyJUXdtkdQ"
)
ACCOUNT_ID = "00000000000"
CREATED_USER = "45e7cec9-af9a-4576-9932-f6262a31ee6a"
CREATED = "2021-04-26T15:31:16.294258+00:00"
LAST_MODIFIED = "2021-04-26T15:31:16.294258+00:00"

file_store_data = {
    "data": {
        "type": "fileStore",
        "attributes": {
            "bucket": "testcustomerpxfbucket",
            "name": "Playlist import test filestore",
            "modificationInfo": {
                "created": CREATED,
                "createdBy": CREATED_USER,
                "lastModified": LAST_MODIFIED,
                "lastModifiedBy": CREATED_USER,
            },
            "topicArn": "arn:aws:sns:us-east-1:123456789012:TestTopic",
            "accessRoleArn": "arn:aws:iam::00000:role/abc",
            "storeType": {"fileFormat": "PXF", "fileClass": "PLAYLIST_IMPORT"},
            "id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a",
            "folderPrefix": "",
        },
    }
}

file_store: FileStore = FILE_STORE_JSONAPI.load(file_store_data)

file_store_db_payload = {
    "tenant": "85d11709-7b87-4eef-8c80-6a670810dfe0",
    "name": "PLAYLIST_IMPORT-52bbcefc-df71-42c8-9ad3-a87c3ac4467a",
    "description": "playlist import file store",
    "bucket": "testcustomerpxfbucket",
    "modificationInfo": {
        "created": CREATED,
        "createdBy": CREATED_USER,
        "lastModified": LAST_MODIFIED,
        "lastModifiedBy": CREATED_USER,
    },
    "topicArn": "arn:aws:sns:us-east-1:123456789012:TestTopic",
    "accessRoleArn": "arn:aws:iam::00000:role/abc",
    "storeType": {"fileFormats": ["pxf"], "fileClass": "PLAYLIST_IMPORT"},
    "id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a",
    "folderPrefix": "",
}

file_store_db: FileStore = FILE_STORE_SCHEMA.load(file_store_db_payload)

file_store_data_2 = {
    "data": {
        "type": "fileStore",
        "attributes": {
            "bucket": "testcustomerpxfbucket",
            "metadata": {},
            "modificationInfo": {
                "created": CREATED,
                "createdBy": CREATED_USER,
                "lastModified": LAST_MODIFIED,
                "lastModifiedBy": CREATED_USER,
            },
            "accessRoleArn": "arn:aws:iam::00000:role/abc",
            "storeType": {"fileFormats": ["pxf"], "fileClass": "PLAYLIST_EXPORT"},
            "name": "playlist import File store 2",
            "id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467b",
            "folderPrefix": "",
        },
    }
}


@pytest.fixture()
def client_lambda_get_file_store_event():
    yield {
        "method_name": "get_file_store_by_id",
        "parameters": {
            "file_store_id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a",
            "tenant_id": "85d11709-7b87-4eef-8c80-6a670810dfe0",
        },
    }


@pytest.fixture(name="lambda_context")
def fixture_lambda_context(request):
    class Context:
        def __init__(self, aws_request_id="1", function_name=request.node.name, function_version=999):
            self.aws_request_id = aws_request_id
            self.function_name = function_name
            self.function_version = function_version
            self.memory_limit_in_mb = 128
            self.invoked_function_arn = "arn:aws:lambda:us-west-1:1234567890:function:test"

    context = Context()
    yield context


@pytest.fixture()
def client_lambda_get_file_store_by_class_event():
    yield {
        "method_name": "get_file_store_by_class",
        "parameters": {"class": FileClass.PLAYLIST_IMPORT.name, "tenant": "85d11709-7b87-4eef-8c80-6a670810dfe0"},
    }


@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"


@pytest.fixture()
def evertz_token():
    yield EVERTZ_TOKEN


@pytest.fixture()
def tenant_token():
    yield TENANT_TOKEN


@pytest.fixture()
def tenant_identity(tenant_token) -> Identity:
    return Identity(token=tenant_token, verified=True)


@pytest.fixture()
def tenant_id_1() -> str:
    yield TENANT_ID


@pytest.fixture()
def user_id() -> str:
    yield "948d2c9e-3611-4943-a321-8aa69395cb85"


@pytest.fixture(scope="session", autouse=True)
def sts():
    with mock_sts():
        yield boto3.client("sts")


@pytest.fixture(scope="session", autouse=True)
def get_caller_identity(sts):
    yield sts.get_caller_identity().get("Account")


table_spec = dict(
    TableName=config.FILE_STORE_DYNAMODB_TABLE,
    AttributeDefinitions=[
        {"AttributeName": "class", "AttributeType": "S"},
        {"AttributeName": "store-id", "AttributeType": "S"},
        {"AttributeName": "tenant-id", "AttributeType": "S"},
    ],
    KeySchema=[{"AttributeName": "tenant-id", "KeyType": "HASH"}, {"AttributeName": "store-id", "KeyType": "RANGE"}],
    LocalSecondaryIndexes=[
        {
            "IndexName": "LSI-1",
            "KeySchema": [
                {"AttributeName": "tenant-id", "KeyType": "HASH"},
                {"AttributeName": "class", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "INCLUDE", "NonKeyAttributes": ["data"]},
        }
    ],
    BillingMode="PAY_PER_REQUEST",
)


@pytest.fixture()
def empty_dynamodb_table():
    with moto.mock_dynamodb():
        ddb = boto3.resource("dynamodb")
        table = ddb.create_table(**table_spec)
        yield table


@pytest.fixture()
def query_dynamodb_table():
    with moto.mock_dynamodb():
        ddb = boto3.resource("dynamodb")
        table = ddb.create_table(**table_spec)

        item = {
            "store-id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a",
            "class": "PLAYLIST_IMPORT",
            "tenant-id": TENANT_ID,
            "data": FILE_STORE_DB_SCHEMA.dump(file_store),
        }

        kwargs = {"Item": item}
        table.put_item(**kwargs)
        yield table


@pytest.fixture()
def query_dynamodb_table_for_all_files_stores():
    with moto.mock_dynamodb():
        ddb = boto3.resource("dynamodb")
        table = ddb.create_table(**table_spec)
        item = {
            "store-id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467a",
            "type": "PLAYLIST_IMPORT",
            "tenant-id": TENANT_ID,
            "data": FILE_STORE_DB_SCHEMA.dump(file_store),
        }
        kwargs = {"Item": item}
        table.put_item(**kwargs)

        file_store_2: FileStore = FILE_STORE_JSONAPI.load(file_store_data_2)
        item = {
            "store-id": "52bbcefc-df71-42c8-9ad3-a87c3ac4467b",
            "type": "PLAYLIST_IMPORT",
            "tenant-id": TENANT_ID,
            "data": FILE_STORE_DB_SCHEMA.dump(file_store_2),
        }
        kwargs = {"Item": item}
        table.put_item(**kwargs)
        yield table


def add_file_store_payload(file_class: str, file_formats: list) -> str:
    return json.dumps(
        {
            "data": {
                "type": "fileStore",
                "attributes": {
                    "storeType": {"fileClass": file_class, "fileFormats": file_formats},
                    "bucket": "testcustomerpxfbucket",
                    "name": f"file store {file_class}",
                    "accessRoleArn": "arn:aws:iam::00000:role/abc",
                    "folderPrefix": "",
                },
            }
        }
    )


def add_file_store_payload_with_metadata(file_class: str, file_formats: list) -> str:
    return json.dumps(
        {
            "data": {
                "type": "fileStore",
                "attributes": {
                    "storeType": {"fileClass": file_class, "fileFormats": file_formats},
                    "bucket": "testcustomerpxfbucket",
                    "name": "file store with metadata",
                    "accessRoleArn": "arn:aws:iam::00000:role/abc",
                    "folderPrefix": "",
                    "metadata": {
                        "translation": {
                            "id": "85d11709-7b87-4eef-8c80-6a670810dfe0",
                            "destination": "85d11709-7b87-4eef-8c80-6a670810dfe0",
                        }
                    },
                },
            }
        }
    )


@pytest.fixture()
@mock_sns
def mock_sns_client():
    sns_client = boto3.client("sns")
    return sns_client


@pytest.fixture()
@mock_sns
def create_mock_sns():
    sns_client = boto3.client("sns")
    topic_arn = sns_client.create_topic(Name="TestTopic", Tags=[{"Key": "file_store_id", "Value": "abcd-1234"}])[
        "TopicArn"
    ]
    sns_client.subscribe(TopicArn=topic_arn, Protocol="sqs")
    return sns_client
