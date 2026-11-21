"""
Shell interativo — entrada 'voce:', saída 'sophia:' com streaming
e exibição de tokens/segundo ao final de cada resposta.
"""

import asyncio
import sys
import time

from config import USER_NAME, ASSISTANT_NAME
from service import MistralService


BANNER = f"""
╔══════════════════════════════════════════════╗
║   NEURACHAT · Mistral 7B · Sophia            ║
║   Digite 'sair' para encerrar                ║
╚══════════════════════════════════════════════╝
"""


async def chat_loop():
    service = MistralService()
    print(BANNER)

    while True:
        try:
            user_input = input(f"\n{USER_NAME}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando...")
            break

        if not user_input:
            continue
        if user_input.lower() in {"sair", "exit", "quit"}:
            print("Até logo!")
            break

        print(f"\n{ASSISTANT_NAME}: ", end="", flush=True)

        start = time.perf_counter()
        first_token_at = None
        token_count = 0

        try:
            async for token in service.stream(user_input):
                if first_token_at is None:
                    first_token_at = time.perf_counter() - start
                token_count += 1
                sys.stdout.write(token)
                sys.stdout.flush()
        except Exception as e:
            print(f"\n[erro] {e}")
            continue

        elapsed = time.perf_counter() - start
        tps = token_count / elapsed if elapsed > 0 else 0.0

        print()
        print(
            f"  ── ttft: {first_token_at:.2f}s | "
            f"tokens: {token_count} | "
            f"tempo: {elapsed:.2f}s | "
            f"vel: {tps:.2f} tok/s"
        )


def main():
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\nEncerrando...")


if __name__ == "__main__":
    main()