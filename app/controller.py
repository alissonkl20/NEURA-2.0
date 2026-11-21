"""
Controller — protocolo de controle entre shell, service e LLM.
Define apenas as interfaces/contratos (sem implementação).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class Message:
    role: str          # "user" | "assistant" | "system"
    content: str


@dataclass
class GenerationStats:
    tokens: int = 0
    elapsed: float = 0.0
    tokens_per_second: float = 0.0


class LLMServiceProtocol(ABC):
    """Protocolo que qualquer Service de LLM deve implementar."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        ...

    @abstractmethod
    def stream(self, prompt: str) -> AsyncIterator[str]:
        ...

    @abstractmethod
    def reset(self) -> None:
        ...