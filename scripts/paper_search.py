#!/usr/bin/env python3
"""Search public paper metadata sources and append hits to the reading queue."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "paper" / "lit_review" / "raw"
DEFAULT_QUEUE = ROOT / "paper" / "lit_review" / "reading_queue.md"
DEFAULT_TIMEOUT = 30
USER_AGENT = "Loomstead paper-search/0.1 (local research workflow)"


def default_ssl_context() -> ssl.SSLContext | None:
    """Use a certifi-backed SSL context when certifi is installed."""

    try:
        import certifi  # type: ignore[import-not-found]
    except Exception:
        return None
    return ssl.create_default_context(cafile=certifi.where())


@dataclass
class PaperResult:
    source: str
    title: str
    year: str = ""
    authors: str = ""
    venue: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    citation_count: str = ""
    raw_id: str = ""


def request_text(url: str, headers: dict[str, str] | None = None) -> str:
    """Send a text request with a workflow-specific User-Agent."""

    req_headers = {"User-Agent": USER_AGENT}
    req_headers.update(headers or {})
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT, context=default_ssl_context()) as response:
        return response.read().decode("utf-8", errors="replace")


def slugify(value: str, limit: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:limit] or "query"


def compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def author_names(authors: Iterable[Any]) -> str:
    names: list[str] = []
    for author in authors:
        if isinstance(author, dict):
            names.append(compact_text(author.get("name") or author.get("display_name")))
        else:
            names.append(compact_text(author))
    return ", ".join(name for name in names if name)


def write_raw(out_dir: Path, source: str, query: str, raw: str, suffix: str) -> Path:
    """Save the raw provider response for later inspection."""

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{stamp}_{source}_{slugify(query)}{suffix}"
    path.write_text(raw, encoding="utf-8", newline="\n")
    return path


def search_semantic_scholar(query: str, limit: int, out_dir: Path) -> list[PaperResult]:
    fields = "title,authors,year,venue,abstract,citationCount,externalIds,url,isOpenAccess,openAccessPdf"
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search?"
        + urllib.parse.urlencode({"query": query, "limit": limit, "fields": fields})
    )
    headers: dict[str, str] = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    raw = request_text(url, headers=headers)
    write_raw(out_dir, "semantic_scholar", query, raw, ".json")
    payload = json.loads(raw)
    results: list[PaperResult] = []
    for item in payload.get("data", []):
        external = item.get("externalIds") or {}
        results.append(
            PaperResult(
                source="semantic_scholar",
                title=compact_text(item.get("title")),
                year=str(item.get("year") or ""),
                authors=author_names(item.get("authors") or []),
                venue=compact_text(item.get("venue")),
                doi=compact_text(external.get("DOI")),
                url=compact_text(item.get("url")),
                abstract=compact_text(item.get("abstract")),
                citation_count=str(item.get("citationCount") or ""),
                raw_id=compact_text(item.get("paperId")),
            )
        )
    return results


def search_openalex(query: str, limit: int, out_dir: Path) -> list[PaperResult]:
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"search": query, "per-page": limit})
    raw = request_text(url)
    write_raw(out_dir, "openalex", query, raw, ".json")
    payload = json.loads(raw)
    results: list[PaperResult] = []
    for item in payload.get("results", []):
        authorships = item.get("authorships") or []
        authors = [a.get("author", {}).get("display_name", "") for a in authorships]
        doi = compact_text(item.get("doi")).replace("https://doi.org/", "")
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        results.append(
            PaperResult(
                source="openalex",
                title=compact_text(item.get("title") or item.get("display_name")),
                year=str(item.get("publication_year") or ""),
                authors=author_names(authors),
                venue=compact_text(source.get("display_name")),
                doi=doi,
                url=compact_text(item.get("doi") or item.get("id")),
                citation_count=str(item.get("cited_by_count") or ""),
                raw_id=compact_text(item.get("id")),
            )
        )
    return results


def search_crossref(query: str, limit: int, out_dir: Path) -> list[PaperResult]:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query": query, "rows": limit})
    raw = request_text(url)
    write_raw(out_dir, "crossref", query, raw, ".json")
    payload = json.loads(raw)
    results: list[PaperResult] = []
    for item in payload.get("message", {}).get("items", []):
        title = compact_text(" ".join(item.get("title") or []))
        authors = [
            " ".join(part for part in [a.get("given", ""), a.get("family", "")] if part)
            for a in item.get("author") or []
        ]
        published = item.get("published-print") or item.get("published-online") or item.get("created") or {}
        year = ""
        if published.get("date-parts"):
            year = str(published["date-parts"][0][0])
        results.append(
            PaperResult(
                source="crossref",
                title=title,
                year=year,
                authors=author_names(authors),
                venue=compact_text(" ".join(item.get("container-title") or [])),
                doi=compact_text(item.get("DOI")),
                url=compact_text(item.get("URL")),
                abstract=compact_text(item.get("abstract")),
                citation_count=str(item.get("is-referenced-by-count") or ""),
                raw_id=compact_text(item.get("DOI")),
            )
        )
    return results


def search_arxiv(query: str, limit: int, out_dir: Path) -> list[PaperResult]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    raw = request_text(url)
    write_raw(out_dir, "arxiv", query, raw, ".xml")
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    results: list[PaperResult] = []
    for entry in root.findall("atom:entry", ns):
        published = compact_text(entry.findtext("atom:published", default="", namespaces=ns))
        authors = [compact_text(a.findtext("atom:name", default="", namespaces=ns)) for a in entry.findall("atom:author", ns)]
        doi = compact_text(entry.findtext("arxiv:doi", default="", namespaces=ns))
        entry_id = compact_text(entry.findtext("atom:id", default="", namespaces=ns))
        results.append(
            PaperResult(
                source="arxiv",
                title=compact_text(entry.findtext("atom:title", default="", namespaces=ns)),
                year=published[:4],
                authors=author_names(authors),
                venue="arXiv",
                doi=doi,
                url=entry_id,
                abstract=compact_text(entry.findtext("atom:summary", default="", namespaces=ns)),
                raw_id=entry_id.rsplit("/", 1)[-1],
            )
        )
    return results


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def append_reading_queue(path: Path, query: str, results: list[PaperResult]) -> None:
    """Append normalized search hits to the queue; formal citations stay in Zotero / BibTeX."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            "# Reading Queue\n\n"
            "| Status | Priority | Paper | Year | Source | Zotero Key | BibTeX Key | Why it matters | Notes |\n"
            "|---|---:|---|---:|---|---|---|---|---|\n",
            encoding="utf-8",
            newline="\n",
        )
    lines = [f"\n<!-- Query: {query} -->"]
    for result in results:
        title = markdown_escape(result.title)
        notes = markdown_escape(result.url or result.doi or result.raw_id)
        lines.append(f"| todo | 2 | {title} | {result.year} | {result.source} |  |  | Search hit for `{query}`. | {notes} |")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


def search_source(source: str, query: str, limit: int, out_dir: Path) -> list[PaperResult]:
    if source == "semantic_scholar":
        return search_semantic_scholar(query, limit, out_dir)
    if source == "openalex":
        return search_openalex(query, limit, out_dir)
    if source == "crossref":
        return search_crossref(query, limit, out_dir)
    if source == "arxiv":
        return search_arxiv(query, limit, out_dir)
    raise ValueError(f"Unsupported source: {source}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Search query.")
    parser.add_argument(
        "--source",
        choices=["all", "semantic_scholar", "openalex", "crossref", "arxiv"],
        default="all",
        help="Metadata source.",
    )
    parser.add_argument("--limit", type=int, default=5, help="Results per source.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Raw response output directory.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE, help="Markdown reading queue to append.")
    parser.add_argument("--json", action="store_true", help="Print normalized JSON results.")
    parser.add_argument("--no-queue", action="store_true", help="Do not append the reading queue.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = ["semantic_scholar", "openalex", "crossref", "arxiv"] if args.source == "all" else [args.source]
    all_results: list[PaperResult] = []
    for source in sources:
        try:
            all_results.extend(search_source(source, args.query, args.limit, args.out_dir))
        except Exception as exc:  # pragma: no cover - network failures should not block other sources
            print(f"[WARN] {source}: {exc}", file=sys.stderr)
    if not args.no_queue:
        append_reading_queue(args.queue, args.query, all_results)
    if args.json:
        print(json.dumps([asdict(result) for result in all_results], ensure_ascii=False, indent=2))
    else:
        print(f"results={len(all_results)} queue={args.queue} raw_dir={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
