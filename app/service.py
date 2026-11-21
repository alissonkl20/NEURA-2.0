"""
Service — camada que conversa com Ollama (Mistral 7B) e devolve output.
Inclui roteamento por keyword, menu de saudação e streaming.
"""

import asyncio
import difflib
import json
import time
import requests
from typing import AsyncIterator, List, Dict

from config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    GENERATION_CONFIG,
    SYSTEM_PROMPT,
    SKILLS_DIR,
    KEYWORD_TO_FILE,
    GREETINGS,
    MENU_FILE,
)
from controller import LLMServiceProtocol, Message, GenerationStats


class MistralService(LLMServiceProtocol):
    def __init__(self, model: str = OLLAMA_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self.host = host.rstrip("/")
        self.history: List[Message] = [
            Message(role="system", content=SYSTEM_PROMPT)
        ]
        self.last_stats = GenerationStats()
        self._greeted = False

    # ---------- Helpers ----------
    def _payload(self, prompt: str, stream: bool) -> Dict:
        messages = [m.__dict__ for m in self.history]
        messages.append({"role": "user", "content": prompt})
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": GENERATION_CONFIG["temperature"],
                "top_p": GENERATION_CONFIG["top_p"],
                "top_k": GENERATION_CONFIG["top_k"],
                "repeat_penalty": GENERATION_CONFIG["repeat_penalty"],
                "num_predict": GENERATION_CONFIG["max_tokens"],
                "num_ctx": GENERATION_CONFIG["num_ctx"],
            },
        }

    def _call_llm(self, prompt: str, max_tokens: int = 300) -> str:
        """Chamada pontual (não-stream) ao Ollama."""
        resp = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "temperature": GENERATION_CONFIG["temperature"],
                    "top_p": GENERATION_CONFIG["top_p"],
                    "num_predict": max_tokens,
                    "num_ctx": GENERATION_CONFIG["num_ctx"],
                },
            },
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()

    def _load_skill(self, filename: str) -> str:
        path = SKILLS_DIR / filename
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    # ---------- Roteamento ----------
    def _is_greeting(self, prompt: str) -> bool:
        if self._greeted:
            return False
        word = prompt.strip().lower().rstrip("?.!")
        return word in GREETINGS

    def _detect_keyword(self, prompt: str) -> str | None:
        """Detecta keyword exata ou por similaridade leve (tolera typos)."""
        word = prompt.strip().lower().rstrip("?.!")

        # 1. Match exato
        if word in KEYWORD_TO_FILE:
            return KEYWORD_TO_FILE[word]

        # 2. Match por similaridade (até ~25% de diferença)
        matches = difflib.get_close_matches(
            word, KEYWORD_TO_FILE.keys(), n=1, cutoff=0.75
        )
        if matches:
            return KEYWORD_TO_FILE[matches[0]]

        return None

    def _menu_response(self) -> str:
        menu = MENU_FILE.read_text(encoding="utf-8") if MENU_FILE.exists() else ""
        prompt = f"""Você é Sophia, assistente de IA do Alisson.

TAREFA: Apresente-se de forma simpática, curta e mostre o menu abaixo.

REGRAS:
- Comece com "Olá! Me chamo Sophia, sou assistente de IA do Alisson."
- Mostre o menu como lista simples, sem inventar nada.
- NÃO use markdown pesado (sem **, sem ###).
- NÃO adicione informações extras.
- Máximo 10 linhas.

MENU:
{menu}"""
        return self._call_llm(prompt, max_tokens=250)

    def _keyword_response(self, filename: str) -> str:
        content = self._load_skill(filename)
        topico = filename.replace(".md", "")
        prompt = f"""Você é Sophia, assistente de IA do Alisson.

O usuário digitou apenas: "{topico}"

TAREFA: Mostrar as informações do tópico "{topico}" de forma natural e direta.

REGRAS OBRIGATÓRIAS:
- Comece já com a informação. NUNCA comece com "O Alisson, aqui!" ou similar.
- Fale SEMPRE em nome do Alisson ("ele", "o Alisson"). NUNCA "eu" ou "meu".
- NÃO misture outros tópicos. Mostre SÓ o conteúdo abaixo.
- NÃO invente nada além do conteúdo.
- Responda em 2-4 frases, sem listar tudo. Se for lista, mostre só os itens principais.
- Tom natural de WhatsApp, sem texto corporativo.

CONTEÚDO:
{content}"""
        return self._call_llm(prompt, max_tokens=350)

    # ---------- API do protocolo ----------
    def generate(self, prompt: str) -> str:
        resp = requests.post(
            f"{self.host}/api/chat",
            json=self._payload(prompt, stream=False),
            timeout=300,
        )
        resp.raise_for_status()
        text = resp.json().get("message", {}).get("content", "")
        self.history.append(Message(role="user", content=prompt))
        self.history.append(Message(role="assistant", content=text))
        return text

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        # ---------- 1) Saudação → menu ----------
        if self._is_greeting(prompt):
            self._greeted = True
            text = self._menu_response()
            for word in text.split(" "):
                yield word + " "
                await asyncio.sleep(0.015)
            self.history.append(Message(role="user", content=prompt))
            self.history.append(Message(role="assistant", content=text))
            return

        # ---------- 2) Keyword pura → .md focado ----------
        keyword_file = self._detect_keyword(prompt)
        if keyword_file:
            text = self._keyword_response(keyword_file)
            for word in text.split(" "):
                yield word + " "
                await asyncio.sleep(0.015)
            self.history.append(Message(role="user", content=prompt))
            self.history.append(Message(role="assistant", content=text))
            return

        # ---------- 3) Fluxo livre → streaming real ----------
        start = time.perf_counter()
        token_count = 0
        buffer: List[str] = []

        with requests.post(
            f"{self.host}/api/chat",
            json=self._payload(prompt, stream=True),
            stream=True,
            timeout=300,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                token = chunk.get("message", {}).get("content", "")
                if token:
                    token_count += 1
                    buffer.append(token)
                    yield token

                if chunk.get("done"):
                    break

        elapsed = time.perf_counter() - start
        self.last_stats = GenerationStats(
            tokens=token_count,
            elapsed=elapsed,
            tokens_per_second=(token_count / elapsed) if elapsed > 0 else 0.0,
        )

        full = "".join(buffer)
        self.history.append(Message(role="user", content=prompt))
        self.history.append(Message(role="assistant", content=full))

    def reset(self) -> None:
        self.history = [Message(role="system", content=SYSTEM_PROMPT)]
        self.last_stats = GenerationStats()
        self._greeted = False