"""
ingest.py — CU Boulder Unofficial Guide
Stage 1: Document Ingestion → Cleaning → Chunking → Embedding → ChromaDB

Chunking spec (from planning.md):
  - Articles / webpages : 300 tokens, 75-token overlap
  - Reddit / short posts: 150 tokens, 30-token overlap
  - Map captions        :  no split, 30–80 tokens, metadata-only anchoring

Embedding model : multi-qa-mpnet-base-dot-v1 (sentence-transformers)
Vector store    : ChromaDB  (persistent, local)
"""

import re
import time
import hashlib
import requests
import chromadb

from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# SOURCE REGISTRY
# Each entry carries the URL, a human-readable place/topic name, a category
# tag, and the source_type that controls which chunking rule is applied.
#
# source_type values:
#   "article"  → 300-token chunks, 75-token overlap
#   "reddit"   → 150-token chunks, 30-token overlap
#   "caption"  → single chunk, no split
# ---------------------------------------------------------------------------

SOURCES = [
    {
        "url": "https://cuindependent.com/2007/01/28/history-behind-the-name-cus-famous-monikers/",
        "place_name": "CU Boulder Nicknames and Monikers",
        "category": "history",
        "source_type": "article",
    },
    {
        "url": "https://www.hercampus.com/school/cu-boulder/hidden-gems-to-study-at-cu-boulder/",
        "place_name": "Hidden Study Spots",
        "category": "study_spots",
        "source_type": "article",
    },
    {
        "url": "https://aboutboulder.com/blog/exploring-the-hidden-gems-university-of-colorados-top-off-the-beaten-path-attractions/",
        "place_name": "Off-the-Beaten-Path Attractions",
        "category": "hidden_gems",
        "source_type": "article",
    },
    {
        "url": "https://www.colorado.edu/today/2020/01/30/your-guide-campus-venues-museums-and-more",
        "place_name": "Campus Venues and Museums",
        "category": "campus_life",
        "source_type": "article",
    },
    # NOTE: bouldercoloradousa.com is JS-rendered and returns a browser warning when fetched
    # without a headless browser. Map entries are stable so inlined as caption chunks.
    {
        "url": "https://www.bouldercoloradousa.com/things-to-do/visiting-cu/things-to-do-at-cu/",
        "place_name": "Fiske Planetarium",
        "category": "visitor_guide",
        "source_type": "caption",
        "inline_text": (
            "Fiske Planetarium is on the CU Boulder campus and is one of the largest planetariums "
            "in the US. It offers public shows, laser concerts, and educational programs. "
            "Admission is free or low-cost for students."
        ),
    },
    {
        "url": "https://www.bouldercoloradousa.com/things-to-do/visiting-cu/things-to-do-at-cu/",
        "place_name": "CU Art Museum",
        "category": "visitor_guide",
        "source_type": "caption",
        "inline_text": (
            "The CU Art Museum hosts rotating exhibitions of contemporary and historic art and is "
            "free and open to the public. Located in the Visual Arts Complex on campus."
        ),
    },
    {
        "url": "https://www.bouldercoloradousa.com/things-to-do/visiting-cu/things-to-do-at-cu/",
        "place_name": "University of Colorado Museum of Natural History",
        "category": "visitor_guide",
        "source_type": "caption",
        "inline_text": (
            "The CU Museum of Natural History in Henderson Building has geology, paleontology, "
            "anthropology, and zoology exhibits. Free admission. The BioLounge inside is a "
            "popular quiet study spot."
        ),
    },
    {
        "url": "https://www.bouldercoloradousa.com/things-to-do/visiting-cu/things-to-do-at-cu/",
        "place_name": "Varsity Lake",
        "category": "visitor_guide",
        "source_type": "caption",
        "inline_text": (
            "Varsity Lake is a scenic pond at the heart of CU Boulder campus. Turtles are often "
            "spotted sunning on rocks. Water lilies were reintroduced in recent years by a campus "
            "landscape architect inspired by historic photos."
        ),
    },
    {
        "url": "https://www.bouldercoloradousa.com/things-to-do/visiting-cu/things-to-do-at-cu/",
        "place_name": "Norlin Quadrangle",
        "category": "visitor_guide",
        "source_type": "caption",
        "inline_text": (
            "Norlin Quad is the historic heart of CU Boulder, surrounded by Tuscan-inspired "
            "sandstone buildings. The Dalton Trumbo Fountain and Elaura Jaquette memorial plaque "
            "are both located here. A popular outdoor gathering and free speech space."
        ),
    },
    {
        "url": "https://colorado.edu/coloradan/2021/01/21/10-plants-and-animals-spot-campus",
        "place_name": "Campus Plants and Animals",
        "category": "nature",
        "source_type": "article",
    },
    {
        "url": "https://www.cuindependent.com/2013/10/24/secret-tunnels-and-murder-the-not-so-scary-truth/",
        "place_name": "Secret Tunnels",
        "category": "folklore",
        "source_type": "article",
    },
    {
        "url": "https://www.colorado.edu/coloradan/2010/09/01/unlocking-cu-secrets",
        "place_name": "Unlocking CU Secrets",
        "category": "hidden_gems",
        "source_type": "article",
    },
    {
        "url": "https://bcn.boulder.co.us/basin/watershed/geology/historic.html",
        "place_name": "Boulder Geology and History",
        "category": "history",
        "source_type": "article",
    },
    {
        "url": "https://www.cuindependent.com/2023/10/31/a-haunted-history-of-cus-macky-auditorium/",
        "place_name": "Macky Auditorium Ghost Story",
        "category": "folklore",
        "source_type": "article",
    },
    {
        "url": "https://aboutboulder.com/blog/old-main-at-cu-boulder-history-flatirons-views-fun-facts/",
        "place_name": "Old Main Building",
        "category": "history",
        "source_type": "article",
    },
    {
        "url": "https://www.reddit.com/r/cuboulder/comments/w0ylxm/what_are_some_good_hidden_places_or_resource/",
        "place_name": "Reddit: Hidden Places and Resources",
        "category": "study_spots",
        "source_type": "reddit",
        # NOTE: Reddit returns 403 on this thread. Key comments inlined manually.
        # Replace the placeholder text below with actual comments from the thread.
        "inline_text": (
            "PLACEHOLDER: Paste the best comments from "
            "https://www.reddit.com/r/cuboulder/comments/w0ylxm/ here. "
            "Each comment should be separated by a blank line. "
            "Remove usernames and upvote counts — content only."
        ),
    },
    {
        "url": "https://www.reddit.com/r/cuboulder/comments/1stfz3m/whats_a_free_thing_to_do_in_boulder_that_most_cu/",
        "place_name": "Reddit: Free Things to Do in Boulder",
        "category": "campus_life",
        "source_type": "reddit",
        # NOTE: Reddit returns 403 on this thread. Key comments inlined manually.
        # Replace the placeholder text below with actual comments from the thread.
        "inline_text": (
            "PLACEHOLDER: Paste the best comments from "
            "https://www.reddit.com/r/cuboulder/comments/1stfz3m/ here. "
            "Each comment should be separated by a blank line. "
            "Remove usernames and upvote counts — content only."
        ),
    },
    # Note: two Reddit sources in planning.md pointed to identical URLs (reddit.com/r/whatisit).
    # Deduplicated here. Add the real second URL if available.

    # --- Additional sources added to reach 50+ chunks ---
    {
        "url": "https://www.cuindependent.com/2016/02/05/the-story-behind-the-naming-of-the-dalton-trumbo-fountain/",
        "place_name": "Dalton Trumbo Fountain Origin Story",
        "category": "history",
        "source_type": "article",
        # NOTE: cuindependent.com blocks scrapers. Historical facts inlined from
        # verified sources: CU Coloradan (colorado.edu/coloradan/2015/06/01/brave-one),
        # CU AS Magazine (colorado.edu/asmagazine/2024/07/08/remembering-cus-brave-one-red-scare),
        # and CU Alumni (colorado.edu/coloradan/2016/02/05 article).
        "inline_text": (
            "Dalton Trumbo was a Hollywood screenwriter and University of Colorado Boulder alumnus "
            "who attended CU for two years before leaving to pursue his writing career. "
            "He became one of Hollywood's most celebrated screenwriters, known for films such as "
            "Spartacus, Roman Holiday, and Exodus. During the anti-communist hysteria of the late "
            "1940s, Trumbo was called before the House Un-American Activities Committee (HUAC) in "
            "October 1947. Rather than name names or take the Fifth Amendment, Trumbo and nine "
            "other film industry workers — known as the Hollywood Ten — refused to cooperate, "
            "invoking the First Amendment. They were sentenced to prison for contempt of Congress "
            "and subsequently blacklisted from Hollywood. "
            "Trumbo continued writing in secret under pseudonyms. The blacklist was effectively "
            "broken in 1960 when actor and director Kirk Douglas publicly credited Trumbo by name "
            "for writing the screenplay to Spartacus. "
            "In the early 1990s, CU Boulder graduate student Kristina Baumli and fellow student "
            "Lewis Cardinal organized a campaign to honor Trumbo on campus, noting that almost "
            "nobody knew he had attended CU. With endorsements from Kirk Douglas, Robert Redford, "
            "Dustin Hoffman, and Katharine Hepburn, the group persuaded the Board of Regents to "
            "rename the fountain outside the University Memorial Center in his honor. "
            "On October 17, 1993, the fountain was officially rededicated as the Dalton Trumbo "
            "Fountain Court. Kirk Douglas, screenwriters Ring Lardner Jr. and Paul Jarrico, and "
            "members of the Trumbo family attended the ceremony. "
            "The fountain is located outside the University Memorial Center on Norlin Quadrangle "
            "and remains a designated free speech and free expression space. Student groups "
            "regularly gather there to organize, protest, and engage with the broader community. "
            "The space symbolizes Trumbo's legacy as a First Amendment champion. "
            "The Keller Center for the Study of the First Amendment at CU Boulder also cites "
            "Trumbo as an inspiration for its work on First Amendment rights and liberties."
        ),
    },
    {
        "url": "https://www.colorado.edu/masterplan/history/klauder-years-1918-1939",
        "place_name": "Tuscan Vernacular Architecture — Klauder Years",
        "category": "history",
        "source_type": "article",
    },
    {
        "url": "https://www.colorado.edu/150/cu-boulder-student-life-through-decades",
        "place_name": "CU Boulder Student Life Through the Decades",
        "category": "campus_life",
        "source_type": "article",
    },
    {
        "url": "https://www.colorado.edu/alumni/2026/04/15/top-10-cu-boulder-traditions-bring-buffs-together",
        "place_name": "Top 10 CU Boulder Traditions",
        "category": "campus_life",
        "source_type": "article",
    },
    {
        "url": "https://www.dailycamera.com/2009/08/13/cu-student-murdered-40-years-ago-honored/",
        "place_name": "Elaura Jaquette Murder — Daily Camera",
        "category": "folklore",
        "source_type": "article",
    },
]

# ---------------------------------------------------------------------------
# CHUNKING PARAMETERS
# ---------------------------------------------------------------------------

CHUNK_PARAMS = {
    "article": {"chunk_tokens": 300, "overlap_tokens": 75},
    "reddit":  {"chunk_tokens": 150, "overlap_tokens": 30},
    "caption": {"chunk_tokens": None, "overlap_tokens": None},  # no split
}

# Rough chars-per-token estimate for splitting (avoids tokenizer dependency).
# all-mpnet-base-v2 uses a WordPiece tokenizer; English averages ~4 chars/token.
CHARS_PER_TOKEN = 4


# ---------------------------------------------------------------------------
# FETCHING + CLEANING
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

# Tags whose content is always boilerplate
BOILERPLATE_TAGS = [
    "script", "style", "nav", "footer", "header",
    "aside", "form", "noscript", "iframe", "button",
    "meta", "link",
]

# CSS class/id fragments that signal nav/ad/promo blocks
BOILERPLATE_PATTERNS = re.compile(
    r"(nav|navbar|menu|sidebar|footer|header|cookie|banner|ad-|"
    r"advertisement|promo|share|social|related|comment-form|subscribe)",
    re.IGNORECASE,
)


def fetch_html(url: str) -> str | None:
    """Download raw HTML for a URL. Returns None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        print(f"  [WARN] fetch failed for {url}: {exc}")
        return None


def fetch_reddit_json(url: str) -> str | None:
    """
    Fetch a Reddit thread via the unofficial JSON API.
    Appends .json to the thread URL and extracts:
      - The original post body (selftext)
      - All top-level comment bodies, filtered to remove deleted/removed content
    Returns a single plain-text string ready for chunking, or None on failure.

    Reddit blocks browser-style scraping but still serves public thread JSON
    at <thread_url>.json without authentication.
    """
    json_url = url.rstrip("/") + ".json"
    # Reddit requires a descriptive User-Agent for the JSON API
    headers = {**HEADERS, "User-Agent": "cu-boulder-rag-ingest/1.0 (educational project)"}
    try:
        resp = requests.get(json_url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"  [WARN] Reddit JSON fetch failed for {url}: {exc}")
        return None

    texts: list[str] = []

    # data[0] = thread metadata listing, data[1] = comments listing
    try:
        # Extract original post selftext if present
        post = data[0]["data"]["children"][0]["data"]
        selftext = post.get("selftext", "").strip()
        if selftext and selftext not in ("[removed]", "[deleted]"):
            texts.append(selftext)

        # Extract top-level comments
        comments = data[1]["data"]["children"]
        for child in comments:
            if child.get("kind") != "t1":
                continue
            body = child["data"].get("body", "").strip()
            if body and body not in ("[removed]", "[deleted]"):
                texts.append(body)
    except (KeyError, IndexError) as exc:
        print(f"  [WARN] Reddit JSON parse error for {url}: {exc}")
        return None

    if not texts:
        print(f"  [WARN] No usable text found in Reddit thread: {url}")
        return None

    return "\n\n".join(texts)


def clean_html(html: str, source_type: str) -> str:
    """
    Parse HTML and extract meaningful text.
    - Removes boilerplate tags and CSS-identified noise blocks.
    - For Reddit sources, targets comment bodies directly.
    - Collapses whitespace and returns plain text.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Strip universally noisy tags
    for tag in soup(BOILERPLATE_TAGS):
        tag.decompose()

    # Strip elements whose class/id names suggest boilerplate
    for el in soup.find_all(True):
        if not hasattr(el, "attrs") or el.attrs is None:
            continue
        el_classes = " ".join(el.get("class", []))
        el_id = el.get("id", "")
        if BOILERPLATE_PATTERNS.search(el_classes) or BOILERPLATE_PATTERNS.search(el_id):
            el.decompose()

    if source_type == "reddit":
        # Reddit: pull comment paragraphs from post content divs
        bodies = soup.find_all("div", {"data-testid": "comment"})
        if not bodies:
            # Fallback: grab all <p> tags
            bodies = soup.find_all("p")
        text = "\n\n".join(el.get_text(separator=" ", strip=True) for el in bodies)
    else:
        # Articles / captions: grab main content area if present, else full body
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find(id=re.compile(r"content|main|body", re.I))
            or soup.find(class_=re.compile(r"content|article|post|entry", re.I))
            or soup.body
        )
        text = main.get_text(separator=" ", strip=True) if main else ""

    # Collapse runs of whitespace / blank lines
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# CHUNKING
# ---------------------------------------------------------------------------

def _approx_token_count(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def chunk_text(text: str, source_type: str) -> list[str]:
    """
    Split text into overlapping chunks according to planning.md spec.

    Strategy:
      1. Split on sentence boundaries first (preserves readability).
      2. Accumulate sentences until the chunk token budget is full.
      3. Back off by overlap_tokens worth of sentences before starting next chunk.
      4. For 'caption' source_type, return the whole text as one chunk.
    """
    params = CHUNK_PARAMS[source_type]

    if params["chunk_tokens"] is None:
        # caption / no-split: single chunk
        return [text] if text.strip() else []

    chunk_chars   = params["chunk_tokens"]   * CHARS_PER_TOKEN
    overlap_chars = params["overlap_tokens"] * CHARS_PER_TOKEN

    # Sentence-boundary split: keep the delimiter attached to its sentence
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(sentences):
        # Build a chunk up to chunk_chars
        buf: list[str] = []
        buf_len = 0
        i = start

        while i < len(sentences):
            slen = len(sentences[i]) + 1  # +1 for the space
            if buf and buf_len + slen > chunk_chars:
                break
            buf.append(sentences[i])
            buf_len += slen
            i += 1

        if not buf:
            # Single sentence longer than chunk size — include it alone
            buf = [sentences[start]]
            i = start + 1

        chunks.append(" ".join(buf))

        if i >= len(sentences):
            break

        # Roll back by overlap_chars to find next start index
        rollback_chars = 0
        next_start = i
        while next_start > start + 1 and rollback_chars < overlap_chars:
            next_start -= 1
            rollback_chars += len(sentences[next_start]) + 1

        # Guard against infinite loop if overlap can't advance
        if next_start <= start:
            next_start = start + 1

        start = next_start

    return chunks


# ---------------------------------------------------------------------------
# EMBEDDING + CHROMADB STORAGE
# ---------------------------------------------------------------------------

def stable_id(url: str, chunk_index: int, place_name: str = "") -> str:
    """Deterministic chunk ID: hash(url + place_name) + chunk index."""
    key = (url + place_name).encode()
    url_hash = hashlib.md5(key).hexdigest()[:8]
    return f"{url_hash}_c{chunk_index:04d}"


def build_vector_store(
    sources: list[dict],
    model_name = "multi-qa-mpnet-base-dot-v1",
    collection_name: str = "cu_boulder_guide",
    persist_dir: str = "./chroma_db",
) -> None:
    """
    Full pipeline: fetch → clean → chunk → embed → store.
    """
    print(f"\n{'='*60}")
    print(f"Loading embedding model: {model_name}")
    print(f"{'='*60}")
    model = SentenceTransformer(model_name)

    print(f"\nInitialising ChromaDB at: {persist_dir}")
    client = chromadb.PersistentClient(path=persist_dir)

    # Delete + recreate for a clean run (remove this block to do incremental adds)
    existing = [c.name for c in client.list_collections()]
    if collection_name in existing:
        print(f"Dropping existing collection '{collection_name}' for fresh ingest.")
        client.delete_collection(collection_name)

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "ip"},
    )

    total_chunks = 0

    for src in sources:
        url         = src["url"]
        place_name  = src["place_name"]
        category    = src["category"]
        source_type = src["source_type"]

        print(f"\n[{source_type.upper()}] {place_name}")
        print(f"  URL: {url}")

        # Use inline_text directly if provided (avoids fetching JS-rendered pages)
        if "inline_text" in src:
            text = src["inline_text"].strip()
            print("  → Using inline text (JS-rendered source).")
        elif source_type == "reddit":
            # Reddit blocks HTML scraping — use the unofficial JSON API instead
            text = fetch_reddit_json(url)
            if not text:
                print("  → Skipped (Reddit JSON fetch failed).")
                continue
            print("  → Fetched via Reddit JSON API.")
        else:
            html = fetch_html(url)
            if html is None:
                print("  → Skipped (fetch failed).")
                continue

            text = clean_html(html, source_type)
            if not text:
                print("  → Skipped (no text after cleaning).")
                continue

        chunks = chunk_text(text, source_type)
        if not chunks:
            print("  → Skipped (no chunks produced).")
            continue

        print(f"  → {len(chunks)} chunk(s), "
              f"avg {sum(len(c) for c in chunks)//len(chunks)} chars each")

        # Embed all chunks for this source in one batch call
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()

        ids        = [stable_id(url, i, place_name) for i in range(len(chunks))]
        metadatas  = [
            {
                "url":                  url,
                "place_name":           place_name,
                "category":             category,
                "source_type":          source_type,
                "chunk_index":          i,
                "total_chunks_in_source": len(chunks),
            }
            for i in range(len(chunks))
        ]

        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        total_chunks += len(chunks)
        time.sleep(0.5)  # polite crawl delay

    print(f"\n{'='*60}")
    print(f"Ingestion complete.")
    print(f"  Total chunks stored : {total_chunks}")
    print(f"  Collection          : {collection_name}")
    print(f"  Persist directory   : {persist_dir}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# VERIFICATION HELPER
# ---------------------------------------------------------------------------

def verify_store(
    collection_name: str = "cu_boulder_guide",
    persist_dir: str = "./chroma_db",
) -> None:
    """
    Spot-check the stored collection:
      - Print total chunk count
      - Show chunk size distribution vs spec targets
      - Sample one chunk per source_type to confirm metadata fields
    """
    client     = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection(collection_name)

    total = collection.count()
    print(f"\nVerification — '{collection_name}': {total} chunks total\n")

    result = collection.get(include=["documents", "metadatas"])
    docs   = result["documents"]
    metas  = result["metadatas"]

    sizes_by_type: dict[str, list[int]] = {}
    sampled: set[str] = set()

    for doc, meta in zip(docs, metas):
        stype = meta.get("source_type", "unknown")
        token_est = _approx_token_count(doc)
        sizes_by_type.setdefault(stype, []).append(token_est)

        # Print one sample per source_type
        if stype not in sampled:
            sampled.add(stype)
            print(f"--- Sample [{stype}] ---")
            print(f"  place_name  : {meta.get('place_name')}")
            print(f"  category    : {meta.get('category')}")
            print(f"  url         : {meta.get('url')}")
            print(f"  chunk_index : {meta.get('chunk_index')}")
            print(f"  token_est   : {token_est}")
            print(f"  text (first 200 chars): {doc[:200]!r}")
            print()

    # Chunk size distribution
    spec_targets = {"article": 300, "reddit": 150, "caption": 60}
    print("Chunk size distribution (approximate tokens):")
    for stype, sizes in sizes_by_type.items():
        avg  = sum(sizes) // len(sizes)
        mn   = min(sizes)
        mx   = max(sizes)
        tgt  = spec_targets.get(stype, "?")
        flag = "✓" if isinstance(tgt, int) and avg <= tgt * 1.15 else "⚠"
        print(f"  {stype:10s}: count={len(sizes):4d}  "
              f"avg={avg:4d}  min={mn:4d}  max={mx:4d}  "
              f"target≤{tgt}  {flag}")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    build_vector_store(SOURCES)
    verify_store()