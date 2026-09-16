import pytest
from pydantic import ValidationError
from validation import Schema, Message, Parameter

def test_valid_schema():
    data = {
        "provider": "ollama",
        "model": "gemma",
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }
    schema = Schema(**data)
    assert schema.provider == "ollama"
    assert schema.model == "gemma"
    assert len(schema.messages) == 1
    assert schema.messages[0].role == "user"
    assert schema.messages[0].content == "Hello"

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

def test_invalid_role():
    data = {
        "provider": "ollama",
        "model": "gemma",
        "messages": [
            {"role": "invalid_role", "content": "Hello"}
        ]
    }
    with pytest.raises(ValidationError):
        Schema(**data)

def test_empty_messages():
    data = {
        "provider": "ollama",
        "model": "gemma",
        "messages": []
    }
    with pytest.raises(ValidationError):
        Schema(**data)

def test_valid_parameters():
    data = {
        "provider": "ollama",
        "model": "gemma",
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
