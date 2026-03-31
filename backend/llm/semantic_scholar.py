"""
Semantic Scholar API client for paper search.
Free tier, no API key required. Optional key improves rate limits.
"""
import time
import httpx
import os

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_FIELDS = "paperId,title,abstract,year,citationCount,authors,tldr,url,openAccessPdf"
_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")


def search_papers(
    query: str,
    limit: int = 8,
    year_range: str | None = None,
    max_retries: int = 2,
) -> list[dict]:
    """
    Search Semantic Scholar for relevant papers.
    Returns a list of formatted paper dicts.

    Args:
        query: Plain-text search query.
        limit: Number of results (max 100).
        year_range: Optional, e.g. "2020-2025" or "2018-" or "2023".
    """
    params: dict = {
        "query": query,
        "fields": _FIELDS,
        "limit": min(limit, 100),
    }
    if year_range:
        params["year"] = year_range

    headers = {}
    if _API_KEY:
        headers["x-api-key"] = _API_KEY

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(BASE_URL, params=params, headers=headers)
            if resp.status_code == 429:
                # Rate limited — back off and retry
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"Semantic Scholar API error {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            papers = data.get("data", [])
            return [_normalize(p) for p in papers]
        except RuntimeError:
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"Semantic Scholar network error: {last_error}")


def _normalize(p: dict) -> dict:
    """Flatten a raw API paper object to a clean dict."""
    authors = [a.get("name", "") for a in (p.get("authors") or [])[:5]]
    tldr_text = ""
    if isinstance(p.get("tldr"), dict):
        tldr_text = p["tldr"].get("text", "")

    url = p.get("url", "")
    if not url:
        oa = p.get("openAccessPdf")
        if isinstance(oa, dict):
            url = oa.get("url", "")

    return {
        "paperId": p.get("paperId", ""),
        "title": p.get("title", ""),
        "authors": authors,
        "year": p.get("year"),
        "citationCount": p.get("citationCount", 0),
        "abstract": (p.get("abstract") or "")[:600],
        "tldr": tldr_text,
        "url": url,
    }


def format_papers_for_prompt(papers: list[dict]) -> str:
    """Convert paper list to a readable block for LLM prompts."""
    if not papers:
        return "（未找到相关论文）"
    lines = []
    for i, p in enumerate(papers, 1):
        authors_str = ", ".join(p["authors"]) if p["authors"] else "Unknown"
        year_str = str(p["year"]) if p["year"] else "N/A"
        cite_str = str(p["citationCount"]) if p["citationCount"] else "0"
        summary = p["tldr"] if p["tldr"] else p["abstract"]
        lines.append(
            f"[{i}] **{p['title']}** ({year_str}, 引用数: {cite_str})\n"
            f"    作者: {authors_str}\n"
            f"    摘要: {summary}\n"
        )
    return "\n".join(lines)
