from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GetEmbeddingRequest(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...

class GetEmbeddingResponse(_message.Message):
    __slots__ = ("vectors",)
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    vectors: str
    def __init__(self, vectors: _Optional[str] = ...) -> None: ...

class NewRecommendationsRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class NewRecommendationsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
