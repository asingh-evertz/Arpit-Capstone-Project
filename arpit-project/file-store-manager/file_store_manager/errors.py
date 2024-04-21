"""
Errors for Channel Orchestration Service
========================

"""

from http import HTTPStatus
from re import findall
from typing import Optional


class ErrorBase(Exception):
    """Base Class For Service Errors"""

    code: str
    title: str
    http_code: HTTPStatus

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if not getattr(cls, "code", None):
            cls.code: str = cls.__name__

        if not getattr(cls, "title", None):
            cls.title: str = " ".join(findall("[A-Z][^A-Z]*", cls.__name__))


class ResourceNotFound(ErrorBase):
    """Generic Not Found Error for Resources"""

    http_code = HTTPStatus.NOT_FOUND
    resource_type: str = ""

    def __init__(self, resource: Optional[str] = "UNKNOWN") -> None:
        super().__init__(f"{self.resource_type} [{resource}] Not Found")


class AccessDenied(ErrorBase):
    """
    Raised when operation is forbidden for the caller
    """

    http_code = HTTPStatus.FORBIDDEN


class ForbiddenAccess(ErrorBase):
    http_code = HTTPStatus.FORBIDDEN

    def __init__(self) -> None:
        super().__init__("Access denied. Please contact an administrator")


class ClientBadRequest(ErrorBase):
    """
    Generic error for client's mistakes
    """

    http_code = HTTPStatus.BAD_REQUEST


class FileStoreConflict(ErrorBase):
    """
    Raised when adding or modifying this file store would conflict with an already
    existing file store
    """

    http_code = HTTPStatus.CONFLICT

    def __init__(self, file_store: Optional[str] = "UNKNOWN") -> None:
        super().__init__(f"File Store [{file_store}] Already Exists")


class FileStoreNotFound(ResourceNotFound):
    """
    This error is raised when a File store is not found.
    """

    resource_type = "FileStore"


class FileStoreIdNotFound(ResourceNotFound):
    """
    This error is raised when a File Store ID is not found.
    """

    resource_type = "FileStoreId"


class TenantIdNotFound(ResourceNotFound):
    """
    This error is raised when a Tenant ID is not found.
    """

    resource_type = "TenantId"


class InvalidFileClass(ClientBadRequest):
    """
    This error is raised when a user requests File Stores of an invalid FileClass type
    """

    def __init__(self, file_class: Optional[str] = "UNKNOWN") -> None:
        super().__init__(f"File Store type [{file_class}] is not a valid FileClass")


class MissingParameter(ErrorBase):
    """
    This Error is raised if parameter is incorrect
    """

    http_code = HTTPStatus.BAD_REQUEST

    def __init__(self, param_name: str = None) -> None:
        super().__init__(f"This param is incorrect [{param_name}]")


class FileStorePatchError(ErrorBase):
    """
    ERROR during channel patch
    """

    http_code = HTTPStatus.BAD_REQUEST


class BucketNameNotFound(ClientBadRequest):
    """
    This error is raised when a user requests File Stores of an invalid Bucket Name
    """

    def __init__(self, bucket_name: Optional[str] = "UNKNOWN") -> None:
        super().__init__(f"Bucket {bucket_name} not found")


class FilestoreNameAlreadyExists(ClientBadRequest):
    """
    This error is raised when file store already exists with the same name
    """

    def __init__(self, name: Optional[str] = "UNKNOWN") -> None:
        super().__init__(f"File store exists with the same name [{name}]")
