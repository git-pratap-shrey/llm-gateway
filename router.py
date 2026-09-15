class Serve_ollama:
    def serve(self, message):
        from providers.ollama_client import OllamaClient

        ollama_client = OllamaClient()
        reply = ollama_client.chat(model=message["model"], messages=message["messages"])
        return reply["message"]["content"]
    

class Serve_gemini:
    def serve(self, message):
        from providers.gemini_client import GeminiClient

        gemini_client = GeminiClient()
        reply = gemini_client.chat(model=message["model"], messages=message["messages"])
        return reply.text

    
class Serve_openrouter:
    def serve(self, message):
        from providers.openrouter_client import OpenrouterClient

        openrouter_client = OpenrouterClient()
        reply = openrouter_client.chat(model=message["model"], messages=message["messages"])
        return reply.choices[0].message.content


class Router:
    def route(self, message):
        if(message["provider"] == "ollama"):
            return Serve_ollama().serve(message)
        
        elif(message["provider"] == "gemini"):
            return Serve_gemini().serve(message)
        
        elif(message["provider"] == "openrouter"):
            return Serve_openrouter().serve(message)