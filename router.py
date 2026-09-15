class serve_ollama:
    def serve(self, message):
        from providers.ollama_client import OllamaClient
        ollama_client = OllamaClient()
        reply = ollama_client.chat(model=message["model"], messages=message["messages"])
        return reply["message"]

class serve_gemini:
    def serve(self, message):
        from providers.gemini_client import GeminiClient
        gemini_client = GeminiClient()
        reply = gemini_client.chat(model=message["model"], messages=message["messages"])
        return reply.text
    
class serve_openrouter:
    def serve(self, message):
        from providers.openrouter_client import OpenrouterClient
        openrouter_client = OpenrouterClient()
        reply = openrouter_client.chat(model=message["model"], messages=message["messages"])
        return reply.choices[0].message.content

class router:
    def route(self, message):
        if(message["provider"] == "ollama"):
            return serve_ollama().serve(message)
        elif(message["provider"] == "gemini"):
            return serve_gemini().serve(message)
        elif(message["provider"] == "openrouter"):
            return serve_openrouter().serve(message)