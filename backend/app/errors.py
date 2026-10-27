"""Application errors and their translation into consistent JSON responses.

Every error response has the shape {"error": {"code", "message", "details"}}.
Unexpected exceptions are logged server-side and reported to clients with a
generic message, so stack traces and internal details are never exposed.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("flowforge")


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_failed"


class PayloadTooLarge(AppError):
    status_code = 413
    code = "file_too_large"


class UnsupportedMediaType(AppError):
    status_code = 415
    code = "unsupported_file_type"


class ServiceUnavailable(AppError):
    status_code = 503
    code = "service_unavailable"


def _body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content=_body(error.code, error.message, error.details))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        problems = [
            {"field": ".".join(str(part) for part in issue.get("loc", []) if part != "body"), "message": issue.get("msg", "")}
            for issue in error.errors()
        ]
        return JSONResponse(
            status_code=422, content=_body("validation_failed", "The request is not valid.", {"problems": problems})
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(error.status_code, "http_error")
        message = error.detail if isinstance(error.detail, str) else "Request failed."
        return JSONResponse(status_code=error.status_code, content=_body(code, message))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500, content=_body("internal_error", "An unexpected error occurred. Check the server log for details.")
        )
