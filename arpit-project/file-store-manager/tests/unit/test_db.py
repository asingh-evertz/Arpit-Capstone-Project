from copy import deepcopy
from uuid import uuid4

import pytest
from errors import FileStoreConflict, FileStoreNotFound
from file_store_client.schemas.file_class import FileClass
from file_store_client.schemas.file_store import FILE_STORE_DB_SCHEMA, FILE_STORE_SCHEMA
from unit.conftest import file_store, file_store_data, file_store_db, file_store_db_payload


def test_put_file_store(empty_dynamodb_table):
    from db import STORE_ID, TENANT_ID, get_file_store_by_id, put_file_store

    put_file_store(file_store_db)

    fs = get_file_store_by_id(file_store_db.tenant, file_store_db.id)

    assert fs.name == file_store_db.name
    assert fs.bucket == file_store.bucket

    with pytest.raises(FileStoreConflict) as err:
        put_file_store(file_store_db)
    assert "Already Exists" in err.value.args[0]

    fsd1 = deepcopy(file_store_db_payload)
    fsd1["id"] = str(uuid4())
    fsd1["storeType"]["fileClass"] = FileClass.CONTENT_SERVICE_BROWSE.name

    fsd2 = deepcopy(file_store_db_payload)
    fsd2["id"] = str(uuid4())
    fsd2["storeType"]["fileClass"] = FileClass.CONTENT_SERVICE_BROWSE.name

    fsd1 = FILE_STORE_SCHEMA.load(fsd1)
    fsd2 = FILE_STORE_SCHEMA.load(fsd2)

    put_file_store(fsd1)

    # A tenant can only have one of this type of FS
    with pytest.raises(FileStoreConflict) as err:
        put_file_store(fsd2)
    assert err.value.args[0] == "File Store [CONTENT_SERVICE_BROWSE] Already Exists"

    fsd3 = deepcopy(file_store_db_payload)
    fsd3["id"] = str(uuid4())
    fsd3["storeType"]["fileClass"] = FileClass.CONTENT_SERVICE_ASSET.name

    fsd4 = deepcopy(file_store_db_payload)
    fsd4["id"] = str(uuid4())
    fsd4["storeType"]["fileClass"] = FileClass.CONTENT_SERVICE_ASSET.name

    fsd3 = FILE_STORE_SCHEMA.load(fsd3)
    fsd4 = FILE_STORE_SCHEMA.load(fsd4)

    # A tenant can have multiple of this class of file store
    put_file_store(fsd3)
    put_file_store(fsd4)


def test_patch_file_store(empty_dynamodb_table):
    from db import STORE_ID, TENANT_ID, get_file_store_by_id, patch_file_store, put_file_store

    put_file_store(file_store_db)
    fs = get_file_store_by_id(file_store_db.tenant, file_store_db.id)
    assert fs.name == file_store_db.name
    assert fs.bucket == file_store_db.bucket

    fsd1 = deepcopy(file_store_db_payload)
    fsd1["storeType"]["fileClass"] = FileClass.CONTENT_SERVICE_ASSET.name
    fsd1["storeType"]["fileFormats"] = ["pxf", "xml"]
    fsd1["accessRoleArn"] = "arn:aws:iam::00000:role/abcde"
    fsd1["bucket"] = "testcustomerpxfbucket"
    fsd1 = FILE_STORE_DB_SCHEMA.load(fsd1)
    patch_file_store(fsd1)
    fs = get_file_store_by_id(fsd1.tenant, fsd1.id)
    assert fs.name == file_store_db.name
    assert fs.bucket == file_store_db.bucket
    assert fs.bucket == fsd1.bucket
    assert fs.store_type.file_formats == fsd1.store_type.file_formats
    assert fs.access_role_arn == fsd1.access_role_arn


def test_get_file_store_by_id(empty_dynamodb_table):
    from db import get_file_store_by_id, put_file_store

    put_file_store(file_store_db)

    fs = get_file_store_by_id(file_store_db.tenant, file_store_db.id)

    assert fs == file_store_db

    with pytest.raises(FileStoreNotFound):
        get_file_store_by_id("tenant", "id")


def test_get_file_stores_by_file_class(empty_dynamodb_table):
    from db import get_file_stores_by_file_class, put_file_store

    # Make copies
    file_stores_data = [deepcopy(file_store_db_payload) for _ in range(3)]

    for fsd in file_stores_data:
        # Give each file store a random UUID
        fsd["id"] = str(uuid4())

    file_stores = [FILE_STORE_DB_SCHEMA.load(data) for data in file_stores_data]

    for fs in file_stores:
        put_file_store(fs)

    fs = get_file_stores_by_file_class(file_stores[0].tenant, file_stores[0].store_type.file_class)

    assert len(fs) == 3
    assert fs == file_stores

    fs = get_file_stores_by_file_class("tenant", FileClass.PLAYLIST_IMPORT)
    assert len(fs) == 0


def test_delete_file_store_by_id(empty_dynamodb_table):
    from db import delete_file_store_by_id, get_file_stores_by_tenant, put_file_store

    # Make copies
    file_stores_data = [deepcopy(file_store_db_payload) for _ in range(3)]

    for fsd in file_stores_data:
        # Give each file store a random UUID
        fsd["id"] = str(uuid4())

    file_stores = [FILE_STORE_DB_SCHEMA.load(data) for data in file_stores_data]

    for fs in file_stores:
        put_file_store(fs)

    fs = get_file_stores_by_tenant(file_stores[0].tenant)
    assert len(fs) == 3

    delete_file_store_by_id(file_stores[0].tenant, file_stores[0].id)

    fs = get_file_stores_by_tenant(file_stores[0].tenant)
    assert len(fs) == 2
