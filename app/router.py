import json
import re
import unicodedata
from pathlib import Path

INDEX_FILE = Path("data_books/index.json")
DATA_DIR = Path("data_books")


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s


def _load_index() -> dict:
    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            f"{INDEX_FILE} não encontrado. Rode: python build_index.py"
        )
    return json.loads(INDEX_FILE.read_text(encoding="utf-8"))


class Router:
    def __init__(self):
        self._index = _load_index()

    def reload(self):
        self._index = _load_index()

    def all_skills(self) -> dict:
        return self._index["skills"]

    def match_triggers(self, pergunta: str) -> list[str]:
        """Retorna IDs de skills que casaram por trigger (0..N)."""
        p = _norm(pergunta)
        hits = []
        for sid, meta in self._index["skills"].items():
            for trig in meta["triggers"]:
                t = _norm(trig)
                if re.search(rf"\b{re.escape(t)}\b", p):
                    hits.append(sid)
                    break
        return hits

    def load_skill_content(self, skill_id: str) -> str:
        meta = self._index["skills"].get(skill_id)
        if not meta:
            return ""
        path = DATA_DIR / meta["file"]
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2].lstrip("\n")
        return text.strip()

    def skill_descriptions(self) -> dict[str, str]:
        return {sid: m["descricao"] for sid, m in self._index["skills"].items()}

    def all_skill_ids(self) -> list[str]:
        return list(self._index["skills"].keys())