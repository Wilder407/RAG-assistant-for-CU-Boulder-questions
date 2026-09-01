"""
script.py — chunk inspection helper

Dumps stored chunks whose place_name or text matches a search term. Written to
diagnose the retrieval failure documented in the README: it answers "what did we
actually store for this source?" independently of whether retrieval finds it.

Usage:
    python script.py Trumbo
    python script.py "Macky"
    python script.py            # no term — summarise the whole collection
"""

import sys

import chromadb

from retrieve import COLLECTION_NAME, PERSIST_DIR

CHARS = 300  # per-chunk preview length


def main() -> None:
    term = sys.argv[1] if len(sys.argv) > 1 else None

    client = chromadb.PersistentClient(path=PERSIST_DIR)
    try:
        col = client.get_collection(COLLECTION_NAME)
    except Exception:
        sys.exit(
            f"Collection '{COLLECTION_NAME}' not found in {PERSIST_DIR}.\n"
            "Build the vector store first: python ingest.py"
        )

    results = col.get(include=["documents", "metadatas"])
    docs = results["documents"]
    metas = results["metadatas"]

    if term is None:
        sources = {m.get("place_name", "?") for m in metas}
        print(f"{len(docs)} chunks across {len(sources)} sources in '{COLLECTION_NAME}'")
        for name in sorted(sources):
            n = sum(1 for m in metas if m.get("place_name") == name)
            print(f"  {n:3}  {name}")
        return

    needle = term.lower()
    matches = 0
    for doc, meta in zip(docs, metas):
        if needle in meta.get("place_name", "").lower() or needle in doc.lower():
            matches += 1
            print(f"{meta.get('place_name', '?')} | chunk {meta.get('chunk_index', '?')}")
            print(doc[:CHARS])
            print()

    print(f"{matches} of {len(docs)} chunks matched {term!r}")


if __name__ == "__main__":
    main()
