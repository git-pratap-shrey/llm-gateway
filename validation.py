"""THE BASE PYDANTIC SCHEMA FOR THE REQUEST BODY OF THE FASTAPI GATEWAY INPUT ENDPOINT"""

from pydantic import BaseModel, Field
from typing import Literal

class Message(BaseModel):
    role : Literal ["system", 
                    "user", 
                    "assistant", 
                    "developer"]
    content : str

class Parameter(BaseModel):
    temperature : float | None = Field(default=None, ge=0.0, le=2.0)
    top_p       : float | None = Field(default=None, ge=0.0, le=1.0)
    top_k       : int   | None = Field(default=None, ge=1)
    max_tokens  : int   | None = Field(default=None, ge=1)

    frequency_penalty : float | None = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty  : float | None = Field(default=None, ge=-2.0, le=2.0)

class Schema(BaseModel):
    provider : Literal ["gemini", "openrouter", "ollama"]
    model    : str
    messages  : list[Message] = Field(min_length=1)
    parameters : Parameter | None = None


# USAGE :
# print(Schema.model_dump())

# schema = Schema(
#     provider="ollama",
#     model="gemma4:cloud",
#     messages=[
#         Message(role="user", content="Hello")
#     ]
# )
# print(schema.model_dump_json())

# schema = Schema.model_validate(dict_data)
# schema = Schema.model_validate_json(json_data)