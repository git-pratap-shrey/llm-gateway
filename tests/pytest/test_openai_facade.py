from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from main import app
from openai_facade import ChatCompletionRequest, OpenAIHTTPError, to_internal


client = TestClient(app)


def request_payload(**overrides):
    payload = {
        "model": "ollama/gemma4:cloud",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    payload.update(overrides)
    return payload


def test_model_is_split_on_first_slash_only():
    schema = to_internal(
        ChatCompletionRequest(**request_payload(model="openrouter/meta-llama/llama-3"))
    )

    assert schema.provider == "openrouter"
    assert schema.model == "meta-llama/llama-3"


@pytest.mark.parametrize("model", ["gemma", "/gemma", "ollama/", "unknown/gemma"])
def test_invalid_model_is_an_openai_error(model):
    with pytest.raises(OpenAIHTTPError) as error:
        to_internal(ChatCompletionRequest(**request_payload(model=model)))

    assert error.value.status_code == 400
    assert error.value.param == "model"
    assert error.value.code == "invalid_model"


def test_translation_flattens_text_and_maps_parameters():
    schema = to_internal(
        ChatCompletionRequest(
            **request_payload(
                messages=[
                    {
                        "role": "developer",
                        "content": [
                            {"type": "text", "text": "Be concise. "},
                            {"type": "text", "text": "Answer now."},
                        ],
                    }
                ],
                temperature=0.4,
                top_p=0.8,
                frequency_penalty=0.2,
                presence_penalty=-0.3,
                max_tokens=25,
                max_completion_tokens=42,
            )
        )
    )

    assert schema.messages[0].content == "Be concise. Answer now."
    assert schema.parameters.model_dump() == {
        "temperature": 0.4,
        "top_p": 0.8,
        "top_k": None,
        "max_tokens": 42,
        "frequency_penalty": 0.2,
        "presence_penalty": -0.3,
    }


@pytest.mark.parametrize(
    ("payload", "param"),
    [
        ({"messages": [{"role": "user", "content": [{"type": "image_url"}]}]}, "messages.content"),
        ({"messages": [{"role": "tool", "content": "Nope"}]}, "messages"),
        ({"stream": True}, "stream"),
        ({"tools": []}, "tools"),
        ({"response_format": {"type": "json_object"}}, "response_format"),
        ({"n": 2}, "n"),
    ],
)
def test_unsupported_features_are_rejected(payload, param):
    request = request_payload()
    request.update(payload)

    with pytest.raises(OpenAIHTTPError) as error:
        to_internal(ChatCompletionRequest(**request))

    assert error.value.status_code == 400
    assert error.value.param == param
    assert error.value.code in {"invalid_request", "unsupported_feature"}


def test_parameter_validation_comes_from_internal_schema():
    with pytest.raises(OpenAIHTTPError) as error:
        to_internal(ChatCompletionRequest(**request_payload(temperature=2.1)))

    assert error.value.status_code == 400
    assert error.value.param == "parameters"


def test_chat_completion_response_and_ignored_field_warning():
    with patch("openai_facade.Router") as router_class:
        router_class.return_value.route.return_value = "Gateway answer"

        response = client.post(
            "/v1/chat/completions",
            json=request_payload(user="customer-42", seed=7),
        )

    assert response.status_code == 200
    assert response.headers["x-gateway-warnings"] == "Ignored fields: seed, user"
    body = response.json()
    assert body["id"].startswith("chatcmpl-")
    assert body["object"] == "chat.completion"
    assert body["model"] == "ollama/gemma4:cloud"
    assert body["choices"] == [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Gateway answer"},
            "finish_reason": "stop",
        }
    ]
    assert body["usage"] is None
    router_class.return_value.route.assert_called_once()


def test_router_exception_is_sanitized_as_upstream_error():
    with patch("openai_facade.Router") as router_class:
        router_class.return_value.route.side_effect = RuntimeError("secret endpoint and key")

        response = client.post("/v1/chat/completions", json=request_payload())

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "message": "The selected model provider could not complete the request.",
            "type": "server_error",
            "param": None,
            "code": "upstream_error",
        }
    }


def test_rate_limit_and_empty_result_are_mapped():
    class RateLimitedError(Exception):
        status_code = 429

    with patch("openai_facade.Router") as router_class:
        router_class.return_value.route.side_effect = RateLimitedError()
        response = client.post("/v1/chat/completions", json=request_payload())
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"

    with patch("openai_facade.Router") as router_class:
        router_class.return_value.route.return_value = None
        response = client.post("/v1/chat/completions", json=request_payload())
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "empty_response"


def test_v1_validation_uses_openai_error_and_api_validation_is_unchanged():
    v1_response = client.post("/v1/chat/completions", json={"model": "ollama/gemma"})
    api_response = client.post("/api/sync", json={"provider": "ollama"})

    assert v1_response.status_code == 400
    assert v1_response.json()["error"]["code"] == "invalid_request"
    assert api_response.status_code == 422
    assert "detail" in api_response.json()


def test_stock_openai_client_can_parse_the_completion():
    with patch("openai_facade.Router") as router_class:
        router_class.return_value.route.return_value = "SDK answer"
        sdk = OpenAI(
            base_url="http://testserver/v1/",
            api_key="not-used",
            http_client=client,
        )
        completion = sdk.chat.completions.create(
            model="ollama/gemma4:cloud",
            messages=[{"role": "user", "content": "Hello"}],
        )

    assert completion.object == "chat.completion"
    assert completion.choices[0].message.content == "SDK answer"
