from router import Router

data_dict = {
    "provider": "gemini",
    "model": "gemma-4-31b-it",
    "messages": [
        {
            "role": "user",
            "content": "Hello, i am john howard"
        }
    ]
}

response = Router().route(data_dict)

print (response)