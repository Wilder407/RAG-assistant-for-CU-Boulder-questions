"""
query.py — CU Boulder Unofficial Guide
Stage 3: Retrieval → Prompt → Generation → Source Attribution

Wires together:
  - retrieve.py  : embeds the query, pulls top-k chunks from ChromaDB
  - Groq API     : generates a grounded answer using llama-3.3-70b-versatile
  - Prompt       : instructs the model to answer from context only
  - Output       : {"answer": str, "sources": list[str]}

Usage (imported by app.py):
    from query import ask
    result = ask("What is the history behind the Dalton Trumbo Fountain?")
    print(result["answer"])
    print(result["sources"])

Usage (standalone):
    python query.py --question "Is Macky Auditorium haunted?"
"""

import argparse
import os

from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer
import chromadb

from retrieve import retrieve, MODEL_NAME, COLLECTION_NAME, PERSIST_DIR, TOP_K

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS  = 512


# ---------------------------------------------------------------------------
# PROMPT TEMPLATE
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a knowledgeable and enthusiastic guide to the University of \
Colorado Boulder campus — the kind of insider who knows the hidden history, folklore, \
tucked-away study spots, and overlooked gems that never make the official tour.

Your job is to answer questions using ONLY the information provided in the context \
documents below. Do not use outside knowledge, invent details, or speculate beyond \
what the documents say.

Rules:
- If the documents contain a clear answer, give it directly and conversationally.
- If the documents contain partial information, share what you know and note the gap.
- If the documents do not contain enough information to answer, say exactly:
  "I don't have enough information on that in my current sources."
- Never fabricate names, dates, locations, or events.
- Keep answers focused and concise — 3 to 6 sentences is ideal unless the question \
requires more detail.
- Do not refer to "the documents" or "the context" in your answer. \
Speak as a knowledgeable guide, not as a system reading files."""


def build_user_prompt(question: str, chunks: list[dict]) -> str:
    """
    Assemble the user-turn prompt by injecting retrieved chunks as numbered
    context blocks, followed by the question.

    Each block includes the source name so the model can ground its answer
    without needing to cite inline — attribution is handled separately in
    the source list appended after generation.
    """
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        block = (
            f"[Document {i}]\n"
            f"Source: {chunk['place_name']} ({chunk['source_type']})\n"
            f"---\n"
            f"{chunk['chunk_text']}"
        )
        context_blocks.append(block)

    context_str = "\n\n".join(context_blocks)

    return (
        f"Context documents:\n\n"
        f"{context_str}\n\n"
        f"---\n\n"
        f"Question: {question}"
    )


# ---------------------------------------------------------------------------
# SOURCE DEDUPLICATION
# ---------------------------------------------------------------------------

def format_sources(chunks: list[dict]) -> list[str]:
    """
    Build a deduplicated, human-readable source list from retrieved chunks.
    Each source appears once even if multiple chunks came from it.
    Format: "Place Name — URL"
    """
    seen: set[str] = set()
    sources: list[str] = []

    for chunk in chunks:
        url        = chunk["url"]
        place_name = chunk["place_name"]
        key        = url  # deduplicate on URL

        if key not in seen:
            seen.add(key)
            sources.append(f"{place_name} — {url}")

    return sources


# ---------------------------------------------------------------------------
# MAIN PIPELINE FUNCTION
# ---------------------------------------------------------------------------

def ask(
    question: str,
    top_k: int = TOP_K,
    model: SentenceTransformer = None,
    collection: chromadb.Collection = None,
    groq_client: Groq = None,
) -> dict:
    """
    End-to-end RAG pipeline: embed query → retrieve chunks → generate answer.

    Accepts optional pre-loaded model, collection, and groq_client so that
    app.py can initialise them once at startup rather than on every request.

    Returns:
        {
            "answer":  str,         # generated answer grounded in retrieved context
            "sources": list[str],   # deduplicated source attributions
            "chunks":  list[dict],  # raw retrieved chunks (for debugging)
        }
    """
    # Lazy initialisation — used when calling ask() directly without pre-loading
    if model is None:
        model = SentenceTransformer(MODEL_NAME)
    if collection is None:
        client     = chromadb.PersistentClient(path=PERSIST_DIR)
        collection = client.get_collection(COLLECTION_NAME)
    if groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY not found. "
                "Add it to your .env file: GROQ_API_KEY=your_key_here"
            )
        groq_client = Groq(api_key=api_key)

    # Stage 1 — Retrieve top-k chunks
    chunks = retrieve(question, model, collection, top_k=top_k)

    # Stage 2 — Build prompt
    user_prompt = build_user_prompt(question, chunks)

    # Stage 3 — Generate with Groq
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
    )
    answer = response.choices[0].message.content.strip()

    # Stage 4 — Build source attribution list
    sources = format_sources(chunks)

    return {
        "answer":  answer,
        "sources": sources,
        "chunks":  chunks,   # available for debugging; app.py doesn't display these
    }


# ---------------------------------------------------------------------------
# STANDALONE ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ask the CU Boulder Unofficial Guide a question."
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        required=True,
        help="Question to ask the guide.",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=TOP_K,
        help=f"Number of chunks to retrieve (default: {TOP_K}).",
    )
    args = parser.parse_args()

    result = ask(args.question, top_k=args.top_k)

    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(result["answer"])

    print("\n" + "=" * 60)
    print("SOURCES")
    print("=" * 60)
    for src in result["sources"]:
        print(f"  • {src}")
    print()
