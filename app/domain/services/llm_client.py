# app/domain/services/llm_client.py

from typing import Protocol, List, Dict, Any

class LLMBackend(Protocol):
    def chat(self, messages: list[dict], model: str) -> Dict[str, Any]:
        """
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
        return:
          {
            "content": "assistant reply text",
            "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
            "raw_model": "grok-llama3" veya "ollama:llama3.1"
          }
        """
        ...

class UnifiedLLMClient:
    def __init__(self, grok_client: LLMBackend, ollama_client: LLMBackend):
        self._grok = grok_client
        self._ollama = ollama_client

    def chat(self, *, backend: str, model: str, messages: list[dict]) -> Dict[str, Any]:
        if backend == "grok":
            return self._grok.chat(messages=messages, model=model)
        elif backend == "ollama":
            return self._ollama.chat(messages=messages, model=model)
        else:
            raise ValueError(f"Unknown backend: {backend}")
