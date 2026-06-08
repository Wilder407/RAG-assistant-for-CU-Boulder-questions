"""
retrieve.py — CU Boulder Unofficial Guide
Stage 2: Embedding + Retrieval

Spec (from planning.md):
  Embedding model : multi-qa-mpnet-base-dot-v1 (sentence-transformers)
  Top-k           : 5 (single retrieval call, no per-type routing)
  Distance metric : cosine (stored in ChromaDB collection metadata)

Usage:
    python retrieve.py                  # runs 3 eval queries and prints results
    python retrieve.py --query "..."    # runs a single custom query

Each returned chunk includes:
  - rank and dot distance from the query
  - source document name (place_name)
  - source URL
  - source_type and category
  - chunk_index and estimated position in the source document
  - chunk text
"""

import argparse
import chromadb

from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# CONFIG — must match ingest.py
# ---------------------------------------------------------------------------

MODEL_NAME      = "multi-qa-mpnet-base-dot-v1"
COLLECTION_NAME = "cu_boulder_guide"
PERSIST_DIR     = "./chroma_db"
TOP_K           = 5


# ---------------------------------------------------------------------------
# RETRIEVAL FUNCTION
# ---------------------------------------------------------------------------

def retrieve(
    query: str,
    model: SentenceTransformer,
    collection: chromadb.Collection,
    top_k: int = TOP_K,
) -> list[dict]:
    """
    Embed a query string and return the top-k most similar chunks.

    Each result dict contains:
        rank          (int)   — 1-based position in the result list
        distance      (float) — dot distance from query (lower = more similar)
        similarity    (float) — 1 - distance, easier to read as a score
        place_name    (str)   — human-readable source document name
        url           (str)   — source URL
        source_type   (str)   — article | reddit | caption
        category      (str)   — e.g. history, folklore, study_spots
        chunk_index   (int)   — position of this chunk within its source document
        chunk_text    (str)   — the raw chunk content
    """
    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # ChromaDB returns nested lists (one per query); unwrap the single query
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    retrieved = []
    for rank, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), start=1):
        retrieved.append(
            {
                "rank":                   rank,
                "distance":               round(dist, 4),
                "similarity":             round(1 - dist, 4),
                "place_name":             meta.get("place_name", "unknown"),
                "url":                    meta.get("url", ""),
                "source_type":            meta.get("source_type", "unknown"),
                "category":               meta.get("category", "unknown"),
                "chunk_index":            meta.get("chunk_index", -1),
                "total_chunks_in_source": meta.get("total_chunks_in_source", "?"),
                "chunk_text":             doc,
            }
        )

    return retrieved


# ---------------------------------------------------------------------------
# DISPLAY HELPER
# ---------------------------------------------------------------------------

def print_results(query: str, results: list[dict]) -> None:
    """Pretty-print retrieval results for a single query."""
    bar = "=" * 70
    print(f"\n{bar}")
    print(f"QUERY: {query}")
    print(bar)

    for r in results:
        # Position label: e.g. "chunk 3 of 7 in source" — we only have chunk_index,
        # not total chunks per source, so we label it as "chunk N (0-indexed)"
        total = r["total_chunks_in_source"]
        position_label = f"chunk {r['chunk_index'] + 1} of {total} in source document"

        print(
            f"\n  Rank {r['rank']}  |  "
            f"distance: {r['distance']:.4f}  |  "
            f"similarity: {r['similarity']:.4f}"
        )
        print(f"  Source   : {r['place_name']}")
        print(f"  URL      : {r['url']}")
        print(f"  Type     : {r['source_type']}  |  category: {r['category']}")
        print(f"  Position : {position_label}")
        print(f"  Text     :")

        # Wrap text at 66 chars for readability, indented
        words = r["chunk_text"].split()
        line, lines = [], []
        for word in words:
            if sum(len(w) + 1 for w in line) + len(word) > 66:
                lines.append("    " + " ".join(line))
                line = [word]
            else:
                line.append(word)
        if line:
            lines.append("    " + " ".join(line))
        print("\n".join(lines))
        print()

    print(bar)


# ---------------------------------------------------------------------------
# EVAL QUERIES (3 of 5 from planning.md)
# ---------------------------------------------------------------------------

EVAL_QUERIES = [
    # Q1 — tests retrieval of a specific named landmark with layered historical context
    "What is the history behind the Dalton Trumbo Fountain?",

    # Q2 — tests retrieval across multiple sources covering the same topic
    "Was there a murder in Macky Auditorium?",

    # Q4 — tests aggregation across multiple short sources (Reddit, Her Campus, CU Today)
    "What are some lesser-known study spots that aren't Norlin Library?",
]


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve top-k chunks from CU Boulder Unofficial Guide."
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default=None,
        help="Custom query string. If omitted, runs the 3 eval queries.",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=TOP_K,
        help=f"Number of results to return (default: {TOP_K}).",
    )
    parser.add_argument(
        "--collection", "-c",
        type=str,
        default=COLLECTION_NAME,
        help=f"ChromaDB collection name (default: {COLLECTION_NAME}).",
    )
    parser.add_argument(
        "--db", "-d",
        type=str,
        default=PERSIST_DIR,
        help=f"Path to ChromaDB persist directory (default: {PERSIST_DIR}).",
    )
    args = parser.parse_args()

    # Load model and collection once — reused across all queries
    print(f"Loading embedding model: {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Connecting to ChromaDB at: {args.db}")
    client     = chromadb.PersistentClient(path=args.db)
    collection = client.get_collection(args.collection)
    print(f"Collection '{args.collection}' — {collection.count()} chunks loaded.\n")

    queries = [args.query] if args.query else EVAL_QUERIES

    for query in queries:
        results = retrieve(query, model, collection, top_k=args.top_k)
        print_results(query, results)

    # Summary: distance statistics across all queries
    if not args.query:
        print("\nDISTANCE SUMMARY (dot; lower = closer to query)")
        print(f"  {'Query':<52}  {'min':>6}  {'max':>6}  {'avg':>6}")
        print(f"  {'-'*52}  {'------':>6}  {'------':>6}  {'------':>6}")
        for query in queries:
            results = retrieve(query, model, collection, top_k=args.top_k)
            dists = [r["distance"] for r in results]
            print(
                f"  {query[:52]:<52}  "
                f"{min(dists):>6.4f}  "
                f"{max(dists):>6.4f}  "
                f"{sum(dists)/len(dists):>6.4f}"
            )
        print()


if __name__ == "__main__":
    main()
