"""Shared error helpers: build the unified error response and an AppError type."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi.responses import JSONResponse

from .common import ErrorBody, ErrorResponse


def new_req_id() -> str:
    return str(uuid.uuid4())


def error_response(
    status_code: int,
    code: str,
    message: str,
    req_id: Optional[str] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=ErrorBody(code=code, message=message, req_id=req_id)
        ).model_dump(),
    )


class AppError(Exception):
    """Raise inside route handlers; a registered handler turns it into error_response."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)
