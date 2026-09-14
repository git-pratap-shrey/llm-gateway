## remaining implementation

# curl -X POST http://localhost:8000/api \
#   -H "Content-Type: application/json" \
#   -d '{
#     "provider": "ollama",
#     "model": "gemma4:cloud",
#     "messages": [
#       {
#         "role": "user",
#         "content": "Hello"
#       }
#     ]
#   }'