"""FileStoreManager Events"""

from dataclasses import dataclass

from evertz_io_events import EvertzIOEvent, EvertzIOEventData
from file_store_client.schemas.file_class import FileClass


@dataclass
class FileStoreCreatedData(EvertzIOEventData):
    """
    Data for the `FileStoreCreated` event
    sns_arn: The ARN of the created SNS Topic
    file_class: The `FileClass` of the created FileStore
    """

    sns_arn: str
    file_class: FileClass


@dataclass
class FileStoreCreated(EvertzIOEvent):
    """Emitted when a file store is created"""

    data: FileStoreCreatedData
