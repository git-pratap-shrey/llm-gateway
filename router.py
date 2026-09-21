from typing import Any

class Serve_ollama:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.ollama_client import OllamaClient

        ollama_client = OllamaClient()
        reply = ollama_client.chat(input)
        return reply["message"]["content"]
        return reply
    

class Serve_gemini:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.gemini_client import GeminiClient

        gemini_client = GeminiClient()
        reply = gemini_client.chat(input)
        return reply.text
        return reply
    

    
class Serve_openrouter:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.openrouter_client import OpenrouterClient

        openrouter_client = OpenrouterClient()
        reply = openrouter_client.chat(input)
        return reply.choices[0].message.content
        return reply


class Router:
    def route(self, input: dict[str, Any]) -> str:
        if(input["provider"] == "ollama"):
            return Serve_ollama().serve(input)
        
        elif(input["provider"] == "gemini"):
            return Serve_gemini().serve(input)
        
        elif(input["provider"] == "openrouter"):
            return Serve_openrouter().serve(input)