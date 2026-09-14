class serve_ollama:
    def __init__(self, message):
        from providers.ollama_client import OllamaClient
        ollama_client = OllamaClient()
        reply = ollama_client.chat(model=message["model"], messages=message["messages"])
        return reply
    
class serve_gemini:
    def __init__(self, message):
        from providers.gemini_client import GeminiClient
        gemini_client = GeminiClient()
        reply = gemini_client.chat(model=message["model"], messages=message["messages"])
        return reply
    
class serve_openrouter:
    def __init__(self, message):
        from providers.openrouter_client import OpenrouterClient
        openrouter_client = OpenrouterClient()
        reply = openrouter_client.chat(model=message["model"], messages=message["messages"])
        return reply

class router:
    def route(self, message):
        if(message["provider"] == "ollama"):
            return serve_ollama(message)
        elif(message["provider"] == "gemini"):
            return serve_gemini(message)
        elif(message["provider"] == "openrouter"):
            return serve_openrouter(message)