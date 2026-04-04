import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    setup_logging(level=settings.LOG_LEVEL)

    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        request.state.request_id = uuid.uuid4()
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %d (%.1fms) request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request.state.request_id,
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            "Validation error | request_id=%s | %s %s | errors=%s",
            request.state.request_id,
            request.method,
            request.url,
            exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid request parameters."},
        )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code >= 500:
            logger.error(
                "HTTP %d | request_id=%s | %s %s | detail=%s",
                exc.status_code,
                request.state.request_id,
                request.method,
                request.url,
                exc.detail,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": "An unexpected error occurred."},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled error | request_id=%s | %s %s",
            request.state.request_id,
            request.method,
            request.url,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()
