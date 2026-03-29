from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

DISCLAIMER = (
    "This analysis is for informational purposes only and is NOT a substitute "
    "for professional medical advice, diagnosis, or treatment. Always consult "
    "a qualified healthcare provider with any questions about your health."
)


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    disclaimer: str = DISCLAIMER

    @classmethod
    def ok(cls, data: T) -> "APIResponse[T]":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "APIResponse[None]":
        return cls(success=False, data=None, error=error)
