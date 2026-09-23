from .rag import build_index


def main() -> None:
    count = build_index(force=True)
    print(f"Indexed {count} knowledge chunks into .chroma")
