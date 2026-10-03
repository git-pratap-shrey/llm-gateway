"""OpenAI Chat Completions compatibility facade.

This module deliberately stops at the HTTP boundary: it translates a small,
well-defined subset of a Chat Completions request into the gateway's existing
``Schema`` and leaves routing and provider adapters unchanged.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal, get_args

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from uuid6 import uuid7

from router import Router
from validation import Schema


logger = logging.getLogger(__name__)
v1 = APIRouter(prefix="/v1")

SUPPORTED_ROLES = frozenset({"system", "developer", "user", "assistant"})
SUPPORTED_PROVIDERS = frozenset(get_args(Schema.model_fields["provider"].annotation))


class OpenAIHTTPError(Exception):
    """An error whose public shape mirrors OpenAI's error envelope."""

    def __init__(
        self,
        status_code: int,
        message: str,
        error_type: str = "invalid_request_error",
        param: str | None = None,
        code: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.error_type = error_type
        self.param = param
        self.code = code
        super().__init__(message)


def openai_error_response(error: OpenAIHTTPError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "message": error.message,
                "type": error.error_type,
                "param": error.param,
                "code": error.code,
            }
        },
    )


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class ChatCompletionRequest(BaseModel):
    """The currently supported Chat Completions subset.

    Extra top-level options are intentionally retained so the route can tell
    callers which options it ignored rather than silently pretending support.
    """

    model_config = ConfigDict(extra="allow")

    model: str
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    stream: bool = False
    tools: Any | None = None
    tool_choice: Any | None = None
    functions: Any | None = None
    response_format: Any | None = None
    n: int | None = Field(default=None, ge=1)


def _unsupported(param: str) -> OpenAIHTTPError:
    return OpenAIHTTPError(
        400,
        f"'{param}' is not supported by this gateway.",
        param=param,
        code="unsupported_feature",
    )


def flatten_content(content: str | list[dict[str, Any]]) -> str:
    """Convert OpenAI text parts to the string content expected by ``Schema``."""

    if isinstance(content, str):
        return content

    text_parts: list[str] = []
    for part in content:
        if part.get("type") != "text":
            raise _unsupported("messages.content")
        text = part.get("text")
        if not isinstance(text, str):
            raise OpenAIHTTPError(
                400,
                "Text message parts must include a string 'text' value.",
                param="messages",
                code="invalid_request",
            )
        text_parts.append(text)
    return "".join(text_parts)


def _parse_model(model: str) -> tuple[str, str]:
    provider, separator, model_name = model.partition("/")
    if not separator or not provider or not model_name or provider not in SUPPORTED_PROVIDERS:
        providers = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise OpenAIHTTPError(
            400,
            f"'model' must be '<provider>/<model>' with provider one of: {providers}.",
            param="model",
            code="invalid_model",
        )
    return provider, model_name


def to_internal(req: ChatCompletionRequest) -> Schema:
    """Translate a facade request into the pre-existing gateway schema."""

    provider, model_name = _parse_model(req.model)

    if req.stream:
        raise _unsupported("stream")
    for field in ("tools", "tool_choice", "functions", "response_format"):
        if getattr(req, field) is not None:
            raise _unsupported(field)
    if req.n is not None and req.n > 1:
        raise _unsupported("n")

    messages: list[dict[str, str]] = []
    for message in req.messages:
        if message.role not in SUPPORTED_ROLES:
            raise OpenAIHTTPError(
                400,
                f"The message role '{message.role}' is not supported.",
                param="messages",
                code="invalid_request",
            )
        messages.append({"role": message.role, "content": flatten_content(message.content)})

    parameter_fields = (
        "temperature",
        "top_p",
        "frequency_penalty",
        "presence_penalty",
    )
    parameters = {
        field: getattr(req, field)
        for field in parameter_fields
        if getattr(req, field) is not None
    }
    max_tokens = req.max_completion_tokens if req.max_completion_tokens is not None else req.max_tokens
    if max_tokens is not None:
        parameters["max_tokens"] = max_tokens

    try:
        return Schema(
            provider=provider,
            model=model_name,
            messages=messages,
            parameters=parameters or None,
        )
    except ValidationError as exc:
        logger.info("OpenAI facade request rejected provider=%s model=%s", provider, model_name)
        raise OpenAIHTTPError(
            400,
            "One or more request parameters are invalid.",
            param="parameters",
            code="invalid_request",
        ) from exc


def completion_response(model: str, content: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid7()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": None,
    }


def _is_rate_limited(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    response = getattr(exc, "response", None)
    status_code = status_code or getattr(response, "status_code", None)
    return status_code == 429


@v1.post("/chat/completions")
def chat_completions(req: ChatCompletionRequest) -> JSONResponse:
    schema = to_internal(req)
    logger.info("OpenAI facade request provider=%s model=%s", schema.provider, schema.model)

    try:
        result = Router().route(schema.model_dump())
    except Exception as exc:
        status_code = 429 if _is_rate_limited(exc) else 502
        code = "rate_limit_exceeded" if status_code == 429 else "upstream_error"
        logger.error(
            "OpenAI facade upstream failure provider=%s model=%s exception_type=%s",
            schema.provider,
            schema.model,
            type(exc).__name__,
        )
        raise OpenAIHTTPError(
            status_code,
            "The selected model provider could not complete the request.",
            error_type="server_error" if status_code == 502 else "rate_limit_error",
            code=code,
        ) from exc

    if not isinstance(result, str) or not result:
        logger.warning("OpenAI facade empty response provider=%s model=%s", schema.provider, schema.model)
        raise OpenAIHTTPError(
            502,
            "The selected model provider returned an empty response.",
            error_type="server_error",
            code="empty_response",
        )

    headers: dict[str, str] = {}
    if req.model_extra:
        headers["X-Gateway-Warnings"] = "Ignored fields: " + ", ".join(sorted(req.model_extra))
    return JSONResponse(content=completion_response(req.model, result), headers=headers)
