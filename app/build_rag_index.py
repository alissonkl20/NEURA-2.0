from rag import RAG


def main():
    rag = RAG()
    total = rag.build_index()

    print(f"\n[ok] Índice RAG criado com {total} trechos.")
    print("[ok] Arquivo: data_books/rag_index.json")


if __name__ == "__main__":
    main()