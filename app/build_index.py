import json
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("Instale: pip install pyyaml")

DATA = Path("data_books")
SKILLS_DIR = DATA / "skills"
INDEX_FILE = DATA / "index.json"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML inválido: {e}")
    return meta, parts[2].lstrip("\n")


def main():
    skills = {}
    for md in sorted(SKILLS_DIR.glob("*.md")):
        meta, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
        sid = meta.get("id") or md.stem
        if not meta.get("triggers"):
            print(f"[skip] {md.name} sem triggers")
            continue
        skills[sid] = {
            "file": f"skills/{md.name}",
            "triggers": meta["triggers"],
            "descricao": meta.get("descricao", ""),
        }
        print(f"[ok] {sid} -> {md.name}")

    INDEX_FILE.write_text(
        json.dumps({"skills": skills}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[index] {len(skills)} skills salvas em {INDEX_FILE}")


if __name__ == "__main__":
    main()