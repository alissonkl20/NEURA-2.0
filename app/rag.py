import json
import math
import re
import requests

from pathlib import Path

DATA_DIR = Path("data_books")
INDEX_PATH = DATA_DIR / "rag_index.json"

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text:latest"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
BATCH_SIZE = 32


class RAG:
    def __init__(self):
        self.chunks = []
        self.embeddings = []

        if INDEX_PATH.exists():
            self.load_index()

    def _embed(self, texts):
        if not texts:
            return []

        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={
                "model": EMBED_MODEL,
                "input": texts,
            },
            timeout=180,
        )
        response.raise_for_status()

        embeddings = response.json().get("embeddings", [])

        if len(embeddings) != len(texts):
            raise RuntimeError(
                "O Ollama retornou uma quantidade incorreta de embeddings."
            )

        return embeddings

    def _split_text(self, text):
        text = text.strip()

        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break

            start = end - CHUNK_OVERLAP

        return chunks

    def _documents(self):
        documents = []

        # Documentos gerais.
        for filename in ("aboutme.md", "abord.md", "corpus.txt"):
            path = DATA_DIR / filename

            if path.exists():
                documents.append((str(path), path.read_text(encoding="utf-8")))

        # Skills.
        skills_dir = DATA_DIR / "skills"

        if skills_dir.exists():
            for path in sorted(skills_dir.glob("*.md")):
                documents.append(
                    (str(path), path.read_text(encoding="utf-8"))
                )

        return documents

    def build_index(self):
        chunks = []

        for source, content in self._documents():
            # Preserva o conteúdo textual, mas remove o frontmatter YAML.
            if content.startswith("---"):
                parts = content.split("---", 2)

                if len(parts) == 3:
                    content = parts[2].strip()

            for number, chunk in enumerate(self._split_text(content)):
                chunks.append({
                    "source": source,
                    "chunk": number,
                    "text": chunk,
                })

        if not chunks:
            raise RuntimeError(
                "Nenhum documento encontrado em data_books/."
            )

        embeddings = []

        for start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[start:start + BATCH_SIZE]
            vectors = self._embed([item["text"] for item in batch])
            embeddings.extend(vectors)

            print(
                f"\r[rag] Indexando {len(embeddings)}/{len(chunks)}",
                end="",
                flush=True,
            )

        print()

        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model": EMBED_MODEL,
            "chunks": chunks,
            "embeddings": embeddings,
        }

        temp_path = INDEX_PATH.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(INDEX_PATH)

        self.chunks = chunks
        self.embeddings = embeddings

        return len(chunks)

    def load_index(self):
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

        if payload.get("model") != EMBED_MODEL:
            raise RuntimeError(
                "O índice foi criado com outro modelo de embeddings. "
                "Reconstrua o índice."
            )

        self.chunks = payload.get("chunks", [])
        self.embeddings = payload.get("embeddings", [])

        if len(self.chunks) != len(self.embeddings):
            raise RuntimeError(
                "Índice inconsistente. Reconstrua o índice."
            )

    @staticmethod
    def _cosine_similarity(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def search(self, query, top_k=4, min_score=0.25):
        if not self.chunks:
            return []

        query = query.strip()

        if not query:
            return []

        query_embedding = self._embed([query])[0]
        results = []

        for chunk, embedding in zip(self.chunks, self.embeddings):
            score = self._cosine_similarity(query_embedding, embedding)

            if score >= min_score:
                results.append({
                    **chunk,
                    "score": round(score, 4),
                })

        results.sort(key=lambda item: item["score"], reverse=True)

        return results[:top_k]

    def retrieve(self, query, top_k=4, min_score=0.25):
        results = self.search(query, top_k, min_score)

        if not results:
            return ""

        blocks = []

        for item in results:
            blocks.append(
                f"Fonte: {item['source']}\n"
                f"Relevância: {item['score']}\n"
                f"Conteúdo:\n{item['text']}"
            )

        return "\n\n---\n\n".join(blocks)