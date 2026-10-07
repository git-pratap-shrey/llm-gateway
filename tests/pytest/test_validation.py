import pytest
from pydantic import ValidationError
from validation import Schema, Message, Parameter


def test_valid_schema():
    data = {
        "provider": "ollama_cloud",
        "model": "gemma4:cloud",
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }
    schema = Schema(**data)
    assert schema.provider == "ollama_cloud"
    assert schema.model == "gemma4:cloud"
    assert len(schema.messages) == 1
    assert schema.messages[0].role == "user"
    assert schema.messages[0].content == "Hello"


def test_valid_schema_gemini():
    data = {
        "provider": "gemini",
        "model": "gemma-4-31b-it",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    schema = Schema(**data)
    assert schema.provider == "gemini"


def test_valid_schema_openrouter():
    data = {
        "provider": "openrouter",
        "model": "meta-llama/llama-3",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    schema = Schema(**data)
    assert schema.provider == "openrouter"


def test_invalid_provider():
    data = {
        "provider": "invalid_provider",
        "model": "gemma",
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }
    with pytest.raises(ValidationError):
        Schema(**data)


def test_ollama_bare_is_invalid():
    """'ollama' (without _cloud) must be rejected — only 'ollama_cloud' is valid."""
    data = {
        "provider": "ollama",
        "model": "gemma",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    with pytest.raises(ValidationError):
        Schema(**data)


def test_invalid_role():
    data = {
        "provider": "ollama_cloud",
        "model": "gemma4:cloud",
        "messages": [
            {"role": "invalid_role", "content": "Hello"}
        ]
    }
    with pytest.raises(ValidationError):
        Schema(**data)


def test_empty_messages():
    data = {
        "provider": "ollama_cloud",
        "model": "gemma4:cloud",
        "messages": []
    }
    with pytest.raises(ValidationError):
        Schema(**data)


def test_valid_parameters():
    data = {
        "provider": "ollama_cloud",
        "model": "gemma4:cloud",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "parameters": {
            "temperature": 0.5,
            "top_p": 0.9,
            "top_k": 40
        }
    }
    schema = Schema(**data)
    assert schema.parameters is not None
    assert schema.parameters.temperature == 0.5
    assert schema.parameters.top_p == 0.9
    assert schema.parameters.top_k == 40


def test_parameters_temperature_out_of_range():
    data = {
        "provider": "ollama_cloud",
        "model": "gemma4:cloud",
        "messages": [{"role": "user", "content": "Hello"}],
        "parameters": {"temperature": 2.5}   # max is 2.0
    }
    with pytest.raises(ValidationError):
        Schema(**data)


def test_parameters_top_p_out_of_range():
    data = {
        "provider": "ollama_cloud",
        "model": "gemma4:cloud",
        "messages": [{"role": "user", "content": "Hello"}],
        "parameters": {"top_p": 1.1}   # max is 1.0
    }
    with pytest.raises(ValidationError):
        Schema(**data)


def test_stream_defaults_false():
    data = {
        "provider": "gemini",
        "model": "gemma-4-31b-it",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    schema = Schema(**data)
    assert schema.stream is False


def test_stream_can_be_set_true():
    data = {
        "provider": "gemini",
        "model": "gemma-4-31b-it",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    }
    schema = Schema(**data)
    assert schema.stream is True


def test_all_valid_roles():
    for role in ("system", "user", "assistant", "developer", "model"):
        data = {
            "provider": "openrouter",
            "model": "meta-llama/llama-3",
            "messages": [{"role": role, "content": "Hello"}]
        }
        schema = Schema(**data)
        assert schema.messages[0].role == role


def test_parameters_none_by_default():
    data = {
        "provider": "gemini",
        "model": "gemma-4-31b-it",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    schema = Schema(**data)
    assert schema.parameters is None
