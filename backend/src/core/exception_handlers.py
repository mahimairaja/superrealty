from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import config
from src.core.exceptions import (
    AuthError,
    DuplicatedError,
    NotFoundError,
    NotSatisfiableError,
    PermissionDeniedError,
    UnauthorizedError,
    ValidationError,
)


def create_error_response(
    status_code: int,
    message: str,
    error: str,
    error_type: str,
    details: Any | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """
    Create a standardized error response format
    """
    response_content = {
        "message": message,
        "error": error,
        "type": error_type,
    }

    if details:
        response_content["details"] = details
    if errors:
        response_content["errors"] = errors

    return JSONResponse(
        status_code=status_code,
        content=response_content,
    )


def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Request validation error: {exc.errors()}")

    errors = [
        {
            "field": ".".join(str(x) for x in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
            "input_value": err.get("input", None),
        }
        for err in exc.errors()
    ]

    return create_error_response(
        status_code=422,
        message="Request validation failed",
        error="Invalid request data",
        error_type="RequestValidationError",
        errors=errors,
    )


def _cors_headers_for(request: Request) -> dict[str, str]:
    """CORS headers to attach to a 500 response.

    The ``Exception`` handler runs in Starlette's ServerErrorMiddleware, which sits OUTSIDE
    CORSMiddleware, so a bare 500 would otherwise return without CORS headers and the browser
    would report a misleading CORS error that masks the real server error. We mirror the app's
    CORS policy here so failures surface as clean, readable JSON in the console. (4xx handlers
    run inside CORSMiddleware and already carry these headers.)
    """
    origin = request.headers.get("origin")
    allowed = config.BACKEND_CORS_ORIGINS or []
    if not origin:
        return {}
    if "*" in allowed:
        return {"Access-Control-Allow-Origin": "*"}
    if origin in allowed:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


def global_exception_handler(request: Request, exc: Exception):
    # Full detail to the server log; generic message to the client unless DEBUG. Wrapped so the
    # handler itself can never raise (which would bypass CORS and surface as a CORS error).
    try:
        logger.error(f"Unexpected error occurred: {exc}", exc_info=True)
        response: JSONResponse = create_error_response(
            status_code=500,
            message="An unexpected error occurred",
            error=str(exc) if config.DEBUG else "Internal server error",
            error_type=exc.__class__.__name__
            if config.DEBUG
            else "InternalServerError",
            details={"path": request.url.path, "method": request.method},
        )
    except Exception:  # noqa: BLE001  (last-resort: always return a valid, CORS-decorated body)
        response = JSONResponse(
            status_code=500,
            content={
                "message": "An unexpected error occurred",
                "error": "Internal server error",
                "type": "InternalServerError",
            },
        )
    for key, value in _cors_headers_for(request).items():
        response.headers[key] = value
    return response


def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    # Never leak SQL / schema details to clients in production.
    logger.error(f"Database error occurred: {exc}", exc_info=True)
    return create_error_response(
        status_code=500,
        message="A database error occurred",
        error=str(exc) if config.DEBUG else "Internal server error",
        error_type="DatabaseError",
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )


def duplicated_error_handler(request: Request, exc: DuplicatedError):
    return create_error_response(
        status_code=400,
        message="Duplicate entry found",
        error=str(exc.detail),
        error_type="DuplicatedError",
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )


def auth_error_handler(request: Request, exc: AuthError):
    return create_error_response(
        status_code=403,
        message="Authentication failed",
        error=str(exc.detail),
        error_type="AuthError",
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )


def not_found_error_handler(request: Request, exc: NotFoundError):
    logger.error(f"Not found error: {exc.detail}")
    return create_error_response(
        status_code=404,
        message="Resource not found",
        error=str(exc.detail),
        error_type="NotFoundError",
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )


def validation_error_handler(request: Request, exc: ValidationError):
    logger.error(f"Validation error: {exc.detail}")
    return create_error_response(
        status_code=422,
        message="Validation failed",
        error=str(exc.detail),
        error_type="ValidationError",
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )


def permission_denied_error_handler(request: Request, exc: PermissionDeniedError):
    return create_error_response(
        status_code=403,
        message="Permission denied",
        error=str(exc.detail),
        error_type="PermissionDeniedError",
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )


def unauthorized_error_handler(request: Request, exc: UnauthorizedError):
    return create_error_response(
        status_code=401,
        message="Unauthorized access",
        error=str(exc.detail),
        error_type="UnauthorizedError",
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )


def not_satisfiable_error_handler(request: Request, exc: NotSatisfiableError):
    return create_error_response(
        status_code=416,
        message="Not satisfiable",
        error=str(exc.detail),
        error_type="NotSatisfiableError",
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )
