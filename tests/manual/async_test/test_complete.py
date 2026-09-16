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

import time

while True:
    output = get_item(job_id)
    print(output)
    if output.get("status") == "completed":
        break
    time.sleep(1)