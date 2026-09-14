class serve_ollama:
    def __init__(self, message):
        from providers.ollama_client import OllamaClient
        ollama_client = OllamaClient()
        ollama_client.chat(model=message["model"], messages=message["messages"])

class serve_gemini:
    def __init__(self, message):
        from providers.gemini_client import GeminiClient
        gemini_client = GeminiClient()
        gemini_client.chat(model=message["model"], messages=message["messages"])

class serve_openrouter:
    def __init__(self, message):
        from providers.openrouter_client import OpenrouterClient
        openrouter_client = OpenrouterClient()
        openrouter_client.chat(model=message["model"], messages=message["messages"])

class route_message:
    def __init__(self, message):
        if(message["provider"] == "ollama"):
            serve_ollama(message)
        elif(message["provider"] == "gemini"):
            serve_gemini(message)
        elif(message["provider"] == "openrouter"):
            serve_openrouter(message)