import json
import sys
import time
import threading
import requests

BASE = "http://127.0.0.1:8000"
STREAM_URL = f"{BASE}/ask/stream"
RELOAD_URL = f"{BASE}/reload-context"
TOPICOS_URL = f"{BASE}/topicos"
REINDEX_URL = f"{BASE}/rebuild-index"

SESSION_ID = "cli"


def fmt_ms(value: float) -> str:
    return f"{value / 1000:.2f}s" if value >= 1000 else f"{value:.0f}ms"


def wait_for_server(retries: int = 15, delay: float = 1.0) -> bool:
    for attempt in range(retries):
        try:
            response = requests.get(BASE, timeout=2)
            response.raise_for_status()
            return True
        except requests.RequestException:
            print(
                f"\r[Aguardando servidor... {attempt + 1}/{retries}]",
                end="",
                flush=True,
            )
            time.sleep(delay)

    print()
    return False


def fetch_topicos() -> dict:
    try:
        response = requests.get(TOPICOS_URL, timeout=10)
        response.raise_for_status()
        return response.json().get("topicos", {})
    except (requests.RequestException, ValueError):
        return {}


def show_intro():
    print("╭─────────────────────────────────────────────╮")
    print("│       Sophia · Assistente de IA             │")
    print("╰─────────────────────────────────────────────╯")
    print()
    print(
        "Olá! Sou a Sophia, assistente de IA do Alisson. "
        "Como posso te ajudar?"
    )
    print("Digite /atalho para consultar os assuntos disponíveis.")
    print()
    print("Comandos: /atalho  /reset  /reload  /reindex  sair")
    print()


def show_atalho():
    topicos = fetch_topicos()

    if not topicos:
        print("\n[erro] Não consegui carregar os assuntos disponíveis.\n")
        return

    print("\n╭─ Assuntos disponíveis ────────────────────────╮")

    for topic_id, metadata in topicos.items():
        descricao = metadata.get("descricao", "").strip()
        nome = topic_id.replace("_", " ").capitalize()

        print(f"│ {nome}:")
        if descricao:
            print(f"│   {descricao}")

    print("╰──────────────────────────────────────────────╯")
    print("Pode perguntar normalmente sobre qualquer assunto.\n")


class Spinner:
    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Pensando"):
        self.message = message
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        index = 0

        while not self._stop.is_set():
            sys.stdout.write(
                f"\r{self.FRAMES[index % len(self.FRAMES)]} "
                f"{self.message}..."
            )
            sys.stdout.flush()
            time.sleep(0.08)
            index += 1

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

        if self._thread.is_alive():
            self._thread.join()

        sys.stdout.write("\r" + " " * (len(self.message) + 12) + "\r")
        sys.stdout.flush()


def stream_call(prompt: str):
    stats = None
    skills_used = []
    first_token = False

    spinner = Spinner()
    spinner.start()

    try:
        with requests.post(
            STREAM_URL,
            json={
                "prompt": prompt,
                "session_id": SESSION_ID,
            },
            stream=True,
            timeout=(10, 600),
        ) as response:

            response.raise_for_status()

            for line in response.iter_lines():
                if not line or not line.startswith(b"data: "):
                    continue

                try:
                    data = json.loads(line[6:].decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                event_type = data.get("type")

                if event_type == "route":
                    skills_used = data.get("skills_used", [])
                    continue

                if event_type == "token":
                    if not first_token:
                        spinner.stop()
                        print("Sophia> ", end="", flush=True)
                        first_token = True

                    print(data.get("token", ""), end="", flush=True)

                elif event_type == "done":
                    stats = data.get("stats")
                    break

                elif event_type == "error":
                    spinner.stop()
                    print(f"\n[erro] {data.get('error', 'Erro desconhecido')}\n")
                    return

        if not first_token:
            spinner.stop()
            print("Sophia> ", end="", flush=True)

        if stats:
            print(
                f"\n\n[stats] "
                f"prompt={stats.get('prompt_tokens', 0)} "
                f"completion={stats.get('completion_tokens', 0)} | "
                f"{stats.get('tokens_per_sec', 0)} tok/s | "
                f"total={fmt_ms(stats.get('total_duration_ms', 0))}"
            )

            if skills_used:
                print(f"[skills] {', '.join(skills_used)}")

            print()

    except requests.RequestException as error:
        spinner.stop()
        print(f"\n[erro de conexão] {error}\n")

    except Exception as error:
        spinner.stop()
        print(f"\n[erro] {error}\n")


def reset_session():
    try:
        response = requests.post(
            f"{BASE}/reset",
            json={"session_id": SESSION_ID},
            timeout=10,
        )
        response.raise_for_status()
        print("[sessão reiniciada]\n")

    except requests.RequestException as error:
        print(f"[erro ao reiniciar sessão] {error}\n")


def reload_context():
    try:
        response = requests.post(RELOAD_URL, timeout=30)
        response.raise_for_status()
        info = response.json()

        print(
            f"[contexto recarregado | "
            f"aboutme={info.get('aboutme_chars', 0)} caracteres | "
            f"skills={info.get('skills', 0)}]\n"
        )

    except requests.RequestException as error:
        print(f"[erro ao recarregar contexto] {error}\n")


def rebuild_index():
    try:
        response = requests.post(REINDEX_URL, timeout=120)
        response.raise_for_status()
        result = response.json()

        print(result.get("stdout", ""))

        if not result.get("ok", True):
            print(result.get("stderr", "[erro ao reconstruir índice]"))

    except requests.RequestException as error:
        print(f"[erro ao reconstruir índice] {error}\n")


def main():
    show_intro()

    if not wait_for_server():
        print("[erro] Servidor não respondeu. Inicie com: python main.py")
        return

    # Não exibe os assuntos automaticamente.
    # Eles aparecem somente quando o usuário digita /atalho.

    while True:
        try:
            prompt = input("você> ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nAté mais!")
            break

        if not prompt:
            continue

        command = prompt.lower().strip()

        if command in ("sair", "exit", "quit"):
            print("Até mais! Se precisar, é só chamar.")
            break

        elif command in ("/atalho", "/topicos", "atalho", "topicos"):
            show_atalho()

        elif command == "/reset":
            reset_session()

        elif command == "/reload":
            reload_context()

        elif command == "/reindex":
            rebuild_index()

        else:
            stream_call(prompt)


if __name__ == "__main__":
    main()