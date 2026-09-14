This is an message-queue based llm gateway, build on fastapi and rabbitmq. 

It allows developers to decouple their llm model into a microservice they can host on their server without worrying about rate limiting and all the providers and the different API protocols for different providers. All that is abstracted away.

In the event of a downtime or batch‑processing LLM requests, the gateway allows users to persist their requests and asynchronously complete them when available.

This also improves reusability among various projects people build, so that they don't have to repeat the same logic everywhere. 