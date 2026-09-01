# The Unofficial Guide to CU Boulder

A retrieval-augmented generation (RAG) system that answers questions about CU Boulder's hidden history, traditions, and lesser-known spots — the kind of stuff you won't hear on an official campus tour.

**[Watch the demo](https://vimeo.com/1199458448?share=copy&fl=sv&fe=ci)**

## Overview

CU Boulder's campus history is scattered across newspaper archives, alumni magazine articles, and Reddit threads. This project consolidates 19 sources — covering campus folklore, hidden study spots, wildlife, and local history — into a single Q&A system built on a full RAG pipeline: ingestion, chunking, embedding, retrieval, and grounded generation.

The result is a tool that can answer things like "Is Macky Auditorium haunted?" or "Tell me about Varsity Lake" with sourced, grounded responses instead of generic LLM knowledge.

## Tech Stack

- **Embeddings:** sentence-transformers (`multi-qa-mpnet-base-dot-v1`)
- **Vector store:** ChromaDB
- **Generation:** Groq API (`openai/gpt-oss-120b`)
- **UI:** Gradio

## Setup

Requires Python 3.11.9 (pinned in `.python-version`) and a free Groq API key from [console.groq.com](https://console.groq.com) — no credit card needed.

**1. Create a virtual environment.** Put it outside any cloud-synced folder. This project lives in iCloud Drive, and syncing a venv's tens of thousands of small binary files is slow and breaks in confusing ways:

```bash
python3 -m venv ~/.venvs/unofficial-guide
source ~/.venvs/unofficial-guide/bin/activate
```

**2. Install dependencies.** Use the lockfile for an environment known to work:

```bash
pip install -r requirements.lock
```

`requirements.txt` states loose intent and is fine for a fresh start, but it will resolve to whatever is current — which is how a rebuild ended up on `chromadb 1.5.9` against code written for `0.6.x`. `requirements.lock` is an exact `pip freeze` of a verified install. Expect roughly 1.5 GB, mostly PyTorch, plus another ~500 MB of model weights cached to `~/.cache/huggingface` on first run.

**3. Add your API key:**

```bash
cp .env.example .env
```

Then replace `your_key_here` with your Groq key. `.env` is gitignored — never commit it. You can also set `GROQ_MODEL` here to override the generation model without touching code.

**4. Build the vector store.** It's gitignored and not in the repo, so this step is required before anything can answer a question:

```bash
python ingest.py
```

This re-scrapes the source URLs, chunks, embeds, and writes `./chroma_db`, then prints per-source chunk statistics. Expect a few sources to fail — some are JS-rendered or have gone behind paywalls since the corpus was first built. A snapshot of the originally ingested text is preserved in `documents/corpus/` (see [Corpus snapshot](#corpus-snapshot)).

**5. Run it:**

```bash
python app.py                                    # Gradio UI on localhost
python query.py -q "Is Macky Auditorium haunted?"  # single question, CLI
python script.py Trumbo                          # inspect stored chunks matching a term
```

## Architecture

**Ingestion & chunking** — different source types need different chunking strategies:

| Source type | Chunk size | Overlap | Rationale |
|---|---|---|---|
| Articles & webpages | 300 tokens | 75 tokens | Long-form content; overlap preserves sentences that straddle boundaries |
| Reddit / short posts | 150 tokens | 30 tokens | Already compact; larger chunks would blend unrelated comments |
| Map captions | 30–80 tokens | None | Self-contained units; tagged with structured metadata (place, source, category) instead |

Final corpus: 95 chunks across 19 sources, stored in ChromaDB.

**Generation model** — the assignment specifies Groq's `llama-3.3-70b-versatile`, but Groq decommissioned that model on the free and developer tiers on 2026-08-16, so it no longer runs. This project uses `openai/gpt-oss-120b`, Groq's own recommended replacement. One consequence worth noting: gpt-oss is a reasoning model, and its internal reasoning tokens draw on the same output budget as the answer, so the token cap was raised from 512 to 1024 and reasoning effort set to `low` — these answers are short grounded summaries, not problems that benefit from extended deliberation.

**Grounded generation** — the system prompt constrains the model to answer only from retrieved context (not training data) and requires every response to surface its source documents. The Gradio UI displays source links alongside each answer, both for transparency and to encourage users to explore further.

## Corpus snapshot

The source registry in [ingest.py](ingest.py) names 22 sources, but the text itself lives on other people's servers — articles get rewritten, sites go behind paywalls, threads get deleted. Since every chunk count and eval result in this README is only meaningful against the text that was actually ingested, `cache_corpus.py` freezes that text to disk:

```bash
python cache_corpus.py            # writes documents/corpus/
python cache_corpus.py --dry-run  # report what would be fetched, write nothing
```

Each source becomes one `.txt` file carrying a provenance header — URL, category, source type, retrieval method, timestamp, and a SHA-256 of the text — alongside `documents/corpus/manifest.json` summarizing the whole run. The cached string is exactly what `ingest.py` would chunk, so the snapshot and the vector store can't drift apart silently.

**Snapshot of 2026-09-01: 17 of 22 sources resolved.** Eight come from `inline_text` in the source registry and always succeed; nine were fetched live. Five failed, all on two hosts (`cuindependent.com` and `aboutboulder.com`) — see below, because the reason turned out not to be the one this README originally gave.

## Known bug: the HTML cleaner deletes some articles

The five failing sources are **not** blocked, paywalled, or JS-gated. Each returns a complete article — 140–157 KB of HTML containing the full text. The text is then destroyed by this project's own cleaner.

`clean_html()` decomposes any element whose class or id matches `BOILERPLATE_PATTERNS` ([ingest.py:282](ingest.py#L282)). On these WordPress themes the outermost page wrapper is `<div class="wrapper-boxed header-style-header-5">`. That matches on `header`, so the wrapper is deleted — and the article lives inside it. Measured on the Macky Auditorium source: 4,016 characters of article text extract cleanly with tag-stripping alone, and 0 characters survive once the class/id pass runs.

The pattern match isn't scoped to the element's own role; it fires on a substring anywhere in the class string and takes every descendant with it. Roughly 23% of the corpus is recoverable by scoping that filter to leaf-ish or known-chrome elements rather than any ancestor.

This supersedes the earlier explanation in **Evaluation** below, which attributed these gaps to JS-rendered pages being blocked from scraping. That was wrong: the fetch always worked. It also explains why eight sources carry hand-written `inline_text` in the registry — those were compensating for this bug rather than for anything on the remote end.

## Key Technical Decision: Fixing a Retrieval Failure

The first version used `all-mpnet-base-v2`, chosen specifically to avoid the 256-token truncation limit of `all-MiniLM-L6-v2`. It looked fine on paper, but evaluation against five natural-language test questions told a different story: queries like *"What is the history of the Dalton Trumbo Fountain?"* were returning chunks about Norlin Quad instead — topically adjacent, but wrong. Cosine distances sat consistently above 0.5 across every test query, a clear signal of weak alignment between query and passage embeddings.

The root cause was a vocabulary mismatch: `all-mpnet-base-v2` is trained for general sentence similarity, not question-to-passage matching, so a natural-language question and a declarative sentence about the same topic land in different regions of the embedding space.

**Fix:** switched to `multi-qa-mpnet-base-dot-v1`, trained on QA pair datasets (including MS MARCO) and built specifically to close that question/answer gap. Retrieval quality improved measurably across every eval query afterward. This also meant switching from cosine to dot-product distance to match how the new model was trained.

## Evaluation

Tested against 5 natural-language questions spanning the corpus (fountain history, a campus murder, wildlife, study spots, Varsity Lake). 4 of 5 were rated relevant with accurate responses; one (wildlife) was partially relevant due to source coverage gaps.

**Failure case:** *"Is Macky Auditorium haunted?"* returned "not enough information," even though the corpus covers the 1966 murder the haunting legend stems from. Root cause: the CU Independent articles most likely to reference the haunting were blocked from scraping (JS-rendered pages), so the system correctly reflected the gap in its actual source material rather than hallucinating an answer.

> **Correction (2026-09-01):** the root cause above is wrong. Those articles were never blocked — they fetch completely, and the cleaner deletes them. See [Known bug: the HTML cleaner deletes some articles](#known-bug-the-html-cleaner-deletes-some-articles). The observed behavior was right and the grounding worked; the diagnosis wasn't.

## Development Notes

Built iteratively with Claude as a pair-programming tool — notably for diagnosing the embedding model mismatch (moving from "the chunk sizes are right but retrieval is still bad" to identifying vocabulary mismatch as the actual cause) and for stress-testing eval questions rather than rewriting them to fit the corpus's limitations, which surfaced the blocked-source problem instead of masking it.

## What I'd Improve

- Add support for JavaScript-rendered sources (several articles, including ones covering campus folklore, were inaccessible via standard scraping)
- Layer in hybrid search (vector + keyword) to catch cases where phrasing diverges from source vocabulary
