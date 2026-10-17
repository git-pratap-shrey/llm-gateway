"""OpenAI Chat Completions compatibility facade.

This module deliberately stops at the HTTP boundary: it translates a small,
well-defined subset of a Chat Completions request into the gateway's existing
``Schema`` and leaves routing and provider adapters unchanged.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal, get_args

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
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
    logger.warning("OpenAI facade unsupported parameter requested: %s", param)
    return OpenAIHTTPError(
        400,
        f"'{param}' is not supported by this gateway.",
        param=param,
        code="unsupported_feature",
    )


def flatten_content(content: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
    """Convert OpenAI content to the value expected by ``Schema``.

    - Plain strings are returned unchanged.
    - Lists that contain only ``text`` parts are collapsed into a single string
      (preserving the previous behaviour for text-only messages).
    - Lists that contain **any** non-text part (e.g. ``image_url``) are returned
      as-is so that the provider's OpenAI-compatible SDK receives the full
      multimodal content array.
    """

    if isinstance(content, str):
        return content

    has_non_text = any(part.get("type") != "text" for part in content)
    if has_non_text:
        # Validate each part minimally and pass the list through unchanged.
        for part in content:
            part_type = part.get("type")
            if part_type == "text" and not isinstance(part.get("text"), str):
                logger.warning("OpenAI facade invalid content: text part missing string 'text'")
                raise OpenAIHTTPError(
                    400,
                    "Text message parts must include a string 'text' value.",
                    param="messages",
                    code="invalid_request",
                )
            if part_type == "image_url":
                img = part.get("image_url")
                if not isinstance(img, dict) or not isinstance(img.get("url"), str):
                    logger.warning("OpenAI facade invalid content: image_url part missing 'url'")
                    raise OpenAIHTTPError(
                        400,
                        "image_url parts must include an 'image_url.url' string.",
                        param="messages",
                        code="invalid_request",
                    )
        return content

    # Text-only list: collapse to a single string (original behaviour).
    text_parts: list[str] = []
    for part in content:
        text = part.get("text")
        if not isinstance(text, str):
            logger.warning("OpenAI facade invalid content: text part missing string 'text'")
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
        logger.warning(
            "OpenAI facade invalid model: '%s'. Must be '<provider>/<model>' with provider one of: %s",
            model,
            providers,
        )
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

    for field in ("tools", "tool_choice", "functions", "response_format"):
        if getattr(req, field) is not None:
            raise _unsupported(field)
    if req.n is not None and req.n > 1:
        raise _unsupported("n")

    messages: list[dict[str, Any]] = []
    for message in req.messages:
        if message.role not in SUPPORTED_ROLES:
            logger.warning(
                "OpenAI facade unsupported role: '%s'. Supported roles: %s",
                message.role,
                sorted(SUPPORTED_ROLES),
            )
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
            stream=req.stream,
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


def sse_chunk(model: str, delta: str, finish_reason: str | None = None) -> str:
    """Build a single server-sent event frame in the OpenAI chat.completion.chunk shape."""
    payload = {
        "id": f"chatcmpl-{uuid7()}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": delta} if delta else {},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(payload)}\n\n"


@v1.post("/chat/completions", response_model=None)
def chat_completions(req: ChatCompletionRequest) -> JSONResponse | StreamingResponse:
    schema = to_internal(req)
    logger.info(
        "OpenAI facade request provider=%s model=%s stream=%s",
        schema.provider, schema.model, schema.stream,
    )

    headers: dict[str, str] = {}
    if req.model_extra:
        ignored = ", ".join(sorted(req.model_extra))
        logger.info("OpenAI facade ignoring extra fields: %s", ignored)
        headers["X-Gateway-Warnings"] = "Ignored fields: " + ignored

    if req.stream:
        def event_stream():
            chunk_count = 0
            start_time = time.perf_counter()
            try:
                for token in Router().stream_route(schema.model_dump()):
                    chunk_count += 1
                    yield sse_chunk(req.model, token)
            except Exception as exc:
                logger.error(
                    "OpenAI facade stream error provider=%s model=%s exception_type=%s: %s",
                    schema.provider, schema.model, type(exc).__name__, exc,
                )
                # HTTP 200 already sent — log and terminate the generator cleanly.
                return
            elapsed = time.perf_counter() - start_time
            logger.info(
                "OpenAI facade stream completed provider=%s model=%s chunks=%d duration=%.2fs",
                schema.provider, schema.model, chunk_count, elapsed,
            )
            yield sse_chunk(req.model, "", finish_reason="stop")
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)

    start_time = time.perf_counter()
    try:
        result = Router().route(schema.model_dump())
    except Exception as exc:
        if type(exc).__name__ == "OllamaModelNotAvailableError":
            logger.error("OpenAI facade missing model: %s", exc)
            raise OpenAIHTTPError(
                404,
                str(exc),
                error_type="invalid_request_error",
                code="model_not_found",
            ) from exc

        status_code = 429 if _is_rate_limited(exc) else 502
        code = "rate_limit_exceeded" if status_code == 429 else "upstream_error"
        logger.error(
            "OpenAI facade upstream failure provider=%s model=%s exception_type=%s: %s",
            schema.provider,
            schema.model,
            type(exc).__name__,
            exc,
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

    elapsed = time.perf_counter() - start_time
    logger.info(
        "OpenAI facade request completed successfully provider=%s model=%s duration=%.2fs",
        schema.provider, schema.model, elapsed,
    )
    return JSONResponse(content=completion_response(req.model, result), headers=headers)
