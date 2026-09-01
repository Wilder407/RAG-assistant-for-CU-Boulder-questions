"""
cache_corpus.py — snapshot the source corpus to disk

The 19 working sources in ingest.SOURCES live on other people's servers. Articles
get rewritten, sites go behind paywalls, Reddit threads get deleted — and the
README's chunk counts and eval results are only meaningful against the text that
was actually ingested. This script freezes that text under documents/corpus/ so
the corpus, and every number derived from it, stays reproducible.

It resolves each source exactly the way ingest.build_vector_store() does — inline
text, Reddit JSON, or fetch-and-clean — so what lands on disk is the same string
that would have been chunked.

Usage:
    python cache_corpus.py            # fetch and write documents/corpus/
    python cache_corpus.py --dry-run  # report what would be fetched, write nothing

Output:
    documents/corpus/<slug>.txt   one file per source, with a provenance header
    documents/corpus/manifest.json  url, method, sha256, char count, status, timestamp
"""

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from ingest import SOURCES, clean_html, fetch_html, fetch_reddit_json

CORPUS_DIR = Path("documents/corpus")
MANIFEST = CORPUS_DIR / "manifest.json"
CRAWL_DELAY = 0.5  # match ingest.py's polite delay


def slugify(name: str) -> str:
    """Filename-safe slug from a place_name. Several sources share a URL, so the
    place_name — not the URL — is what keeps filenames distinct."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug or "source"


def resolve_text(src: dict) -> tuple[str | None, str]:
    """
    Return (text, method) for one source, mirroring ingest.build_vector_store().
    text is None when the source could not be resolved.
    """
    if "inline_text" in src:
        return src["inline_text"].strip(), "inline_text"

    if src["source_type"] == "reddit":
        return fetch_reddit_json(src["url"]), "reddit_json"

    html = fetch_html(src["url"])
    if html is None:
        return None, "fetch_html"

    text = clean_html(html, src["source_type"])
    return (text or None), "fetch_html"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be fetched without writing files.",
    )
    args = parser.parse_args()

    if not args.dry_run:
        CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries: list[dict] = []
    ok = failed = 0

    for i, src in enumerate(SOURCES, start=1):
        name = src["place_name"]
        print(f"[{i:2}/{len(SOURCES)}] {name}")

        if args.dry_run:
            method = (
                "inline_text" if "inline_text" in src
                else "reddit_json" if src["source_type"] == "reddit"
                else "fetch_html"
            )
            print(f"          would resolve via {method}")
            continue

        text, method = resolve_text(src)
        slug = slugify(name)

        if not text:
            print("          FAILED — no text resolved")
            failed += 1
            entries.append({
                "place_name": name,
                "url": src["url"],
                "category": src["category"],
                "source_type": src["source_type"],
                "method": method,
                "status": "failed",
                "file": None,
                "chars": 0,
                "sha256": None,
                "cached_at": stamp,
            })
        else:
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            path = CORPUS_DIR / f"{slug}.txt"
            header = (
                f"# place_name : {name}\n"
                f"# url        : {src['url']}\n"
                f"# category   : {src['category']}\n"
                f"# source_type: {src['source_type']}\n"
                f"# method     : {method}\n"
                f"# cached_at  : {stamp}\n"
                f"# sha256     : {digest}\n"
                f"#\n"
                f"# Text below is the exact string ingest.py would chunk. Do not edit.\n"
                f"{'-' * 74}\n"
            )
            path.write_text(header + text + "\n", encoding="utf-8")
            print(f"          {len(text):>7,} chars via {method} -> {path}")
            ok += 1
            entries.append({
                "place_name": name,
                "url": src["url"],
                "category": src["category"],
                "source_type": src["source_type"],
                "method": method,
                "status": "ok",
                "file": str(path.relative_to("documents")),
                "chars": len(text),
                "sha256": digest,
                "cached_at": stamp,
            })

        if method != "inline_text":
            time.sleep(CRAWL_DELAY)

    if args.dry_run:
        print(f"\nDry run — {len(SOURCES)} sources, nothing written.")
        return 0

    MANIFEST.write_text(
        json.dumps(
            {
                "cached_at": stamp,
                "sources_total": len(SOURCES),
                "sources_ok": ok,
                "sources_failed": failed,
                "entries": entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\n{'=' * 60}")
    print(f"Cached {ok} of {len(SOURCES)} sources ({failed} failed)")
    print(f"Manifest: {MANIFEST}")
    print(f"{'=' * 60}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
