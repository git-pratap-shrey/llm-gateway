from router import Router

data_dict = {
    "provider": "ollama",
    "model": "gemma4:cloud",
    "messages": [
        {
            "role": "user",
            "content": "Hello, i am john howard"
        }
    ]
}
response = Router().route(data_dict)

print (response)