# The Unofficial Guide to CU Boulder

A retrieval-augmented generation (RAG) system that answers questions about CU Boulder's hidden history, traditions, and lesser-known spots — the kind of stuff you won't hear on an official campus tour.

**[Watch the demo](https://vimeo.com/1199458448?share=copy&fl=sv&fe=ci)**

## Overview

CU Boulder's campus history is scattered across newspaper archives, alumni magazine articles, and Reddit threads. This project consolidates 19 sources — covering campus folklore, hidden study spots, wildlife, and local history — into a single Q&A system built on a full RAG pipeline: ingestion, chunking, embedding, retrieval, and grounded generation.

The result is a tool that can answer things like "Is Macky Auditorium haunted?" or "Tell me about Varsity Lake" with sourced, grounded responses instead of generic LLM knowledge.

## Tech Stack

- **Embeddings:** sentence-transformers (`multi-qa-mpnet-base-dot-v1`)
- **Vector store:** ChromaDB
- **Generation:** Groq API
- **UI:** Gradio

## Architecture

**Ingestion & chunking** — different source types need different chunking strategies:

| Source type | Chunk size | Overlap | Rationale |
|---|---|---|---|
| Articles & webpages | 300 tokens | 75 tokens | Long-form content; overlap preserves sentences that straddle boundaries |
| Reddit / short posts | 150 tokens | 30 tokens | Already compact; larger chunks would blend unrelated comments |
| Map captions | 30–80 tokens | None | Self-contained units; tagged with structured metadata (place, source, category) instead |

Final corpus: 95 chunks across 19 sources, stored in ChromaDB.

**Grounded generation** — the system prompt constrains the model to answer only from retrieved context (not training data) and requires every response to surface its source documents. The Gradio UI displays source links alongside each answer, both for transparency and to encourage users to explore further.

## Key Technical Decision: Fixing a Retrieval Failure

The first version used `all-mpnet-base-v2`, chosen specifically to avoid the 256-token truncation limit of `all-MiniLM-L6-v2`. It looked fine on paper, but evaluation against five natural-language test questions told a different story: queries like *"What is the history of the Dalton Trumbo Fountain?"* were returning chunks about Norlin Quad instead — topically adjacent, but wrong. Cosine distances sat consistently above 0.5 across every test query, a clear signal of weak alignment between query and passage embeddings.

The root cause was a vocabulary mismatch: `all-mpnet-base-v2` is trained for general sentence similarity, not question-to-passage matching, so a natural-language question and a declarative sentence about the same topic land in different regions of the embedding space.

**Fix:** switched to `multi-qa-mpnet-base-dot-v1`, trained on QA pair datasets (including MS MARCO) and built specifically to close that question/answer gap. Retrieval quality improved measurably across every eval query afterward. This also meant switching from cosine to dot-product distance to match how the new model was trained.

## Evaluation

Tested against 5 natural-language questions spanning the corpus (fountain history, a campus murder, wildlife, study spots, Varsity Lake). 4 of 5 were rated relevant with accurate responses; one (wildlife) was partially relevant due to source coverage gaps.

**Failure case:** *"Is Macky Auditorium haunted?"* returned "not enough information," even though the corpus covers the 1966 murder the haunting legend stems from. Root cause: the CU Independent articles most likely to reference the haunting were blocked from scraping (JS-rendered pages), so the system correctly reflected the gap in its actual source material rather than hallucinating an answer.

## Development Notes

Built iteratively with Claude as a pair-programming tool — notably for diagnosing the embedding model mismatch (moving from "the chunk sizes are right but retrieval is still bad" to identifying vocabulary mismatch as the actual cause) and for stress-testing eval questions rather than rewriting them to fit the corpus's limitations, which surfaced the blocked-source problem instead of masking it.

## What I'd Improve

- Add support for JavaScript-rendered sources (several articles, including ones covering campus folklore, were inaccessible via standard scraping)
- Layer in hybrid search (vector + keyword) to catch cases where phrasing diverges from source vocabulary
