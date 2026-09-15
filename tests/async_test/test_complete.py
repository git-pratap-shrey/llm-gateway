from main import process_async, get_item
from validation import Schema

schema = Schema(
    provider="ollama",
    model="gemma4:cloud",
    messages=[
        {
            "role": "user",
            "content": "Hello"
        }
    ]
)
response = process_async(schema)

job_id = response["job_id"]

print(response)

while True:
    output = get_item(job_id)
    print(output)