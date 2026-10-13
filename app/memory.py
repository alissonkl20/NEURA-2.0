import json
import math
import sqlite3

from pathlib import Path
from datetime import datetime, timezone

import requests

DB_PATH = Path("data_books/memory.db")

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text:latest"


class ConversationMemory:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, id)
            """)

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

        vectors = response.json().get("embeddings", [])

        if len(vectors) != len(texts):
            raise RuntimeError(
                "Quantidade incorreta de embeddings retornados."
            )

        return vectors

    @staticmethod
    def _cosine_similarity(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if not norm_a or not norm_b:
            return 0.0

        return dot / (norm_a * norm_b)

    def add_turn(self, session_id, user_text, assistant_text):
        messages = [
            ("user", user_text),
            ("assistant", assistant_text),
        ]

        vectors = self._embed([text for _, text in messages])
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO messages (
                    session_id, role, content, embedding, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        session_id,
                        role,
                        content,
                        json.dumps(vector),
                        now,
                    )
                    for (role, content), vector in zip(messages, vectors)
                    if content.strip()
                ],
            )

    def recent_messages(self, session_id, limit=12):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()

        return [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]

    def search(self, session_id, query, top_k=4, min_score=0.35):
        query = query.strip()

        if not query:
            return []

        query_vector = self._embed([query])[0]

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, role, content, embedding, created_at
                FROM messages
                WHERE session_id = ?
                  AND embedding IS NOT NULL
                ORDER BY id DESC
                LIMIT 2000
                """,
                (session_id,),
            ).fetchall()

        results = []

        for row in rows:
            try:
                vector = json.loads(row["embedding"])
            except (TypeError, json.JSONDecodeError):
                continue

            score = self._cosine_similarity(query_vector, vector)

            if score >= min_score:
                results.append({
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "score": round(score, 4),
                })

        results.sort(key=lambda item: item["score"], reverse=True)

        return results[:top_k]

    def retrieve(self, session_id, query, top_k=4):
        results = self.search(session_id, query, top_k=top_k)

        if not results:
            return ""

        blocks = []

        for item in results:
            blocks.append(
                f"Data: {item['created_at']}\n"
                f"Autor: {item['role']}\n"
                f"Relevância: {item['score']}\n"
                f"Mensagem: {item['content']}"
            )

        return "\n\n---\n\n".join(blocks)

    def reset_session(self, session_id):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_id,),
            )

    def count_messages(self, session_id=None):
        with self._connect() as connection:
            if session_id is None:
                row = connection.execute(
                    "SELECT COUNT(*) AS total FROM messages"
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM messages
                    WHERE session_id = ?
                    """,
                    (session_id,),
                ).fetchone()

        return row["total"]