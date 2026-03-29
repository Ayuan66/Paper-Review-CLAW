"""
Fetch and summarize venue (conference/journal) review guidelines.

Flow:
  1. Fetch HTML from each URL for the venue (stop at first success)
  2. Strip HTML tags -> plain text
  3. Call LLM to extract review criteria in Chinese
  4. Cache result in memory (key = venue_id) so repeated calls don't re-fetch
"""

import re
import html as html_lib
from html.parser import HTMLParser
from datetime import datetime
import httpx

from config import VENUES

# In-memory cache: venue_id -> {"context": str, "fetched_at": str}
_venue_cache: dict[str, dict] = {}

_SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link"}


class _TextExtractor(HTMLParser):
    """Minimal HTML -> plain text extractor."""
    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in _SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        if tag.lower() in {"p", "div", "li", "h1", "h2", "h3", "h4", "br", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip == 0:
            text = data.strip()
            if text:
                self.parts.append(text)

    def get_text(self) -> str:
        raw = " ".join(self.parts)
        # Collapse whitespace
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r" {2,}", " ", raw)
        return html_lib.unescape(raw).strip()


def _fetch_page_text(url: str, max_chars: int = 8000) -> str | None:
    """Return page plain text, or None on failure."""
    try:
        resp = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PaperReviewBot/1.0)"},
        )
        if resp.status_code != 200:
            return None
        parser = _TextExtractor()
        parser.feed(resp.text)
        text = parser.get_text()
        return text[:max_chars] if text else None
    except Exception:
        return None


def _summarize_venue(venue_id: str, raw_text: str, llm_client) -> str:
    """Use LLM to extract venue-specific review criteria from raw page text."""
    venue_info = VENUES[venue_id]
    prompt = f"""以下是从 {venue_info['name']} 官网抓取的页面内容：

---
{raw_text}
---

请基于以上内容，提炼出该{'会议' if venue_info['type'] == 'conference' else '期刊'}对投稿论文的具体要求，包括：
1. 研究范围和主题范围（Topics of Interest）
2. 论文类型和格式要求
3. 评审标准和重点关注点
4. 该venue的特色和偏好（如更重视工业实践、理论创新、实证研究等）
5. 常见拒稿原因（如有）

请用中文回答，结构清晰，要点明确。如果页面内容中没有足够信息，请根据你对该venue的了解进行补充说明。"""

    try:
        # Use the editor model (DeepSeek) for summarization - it's fast and capable
        from config import DEFAULT_MODELS
        model = DEFAULT_MODELS.get("editor", "deepseek/deepseek-chat")
        return llm_client.chat_text(
            model=model,
            system_prompt="你是一位熟悉软件工程顶级学术会议和期刊的专家。",
            user_prompt=prompt,
            max_tokens=2048,
        )
    except Exception as e:
        return f"（venue信息提炼失败：{e}）"


def get_venue_context(venue_id: str, llm_client, force_refresh: bool = False) -> str:
    """
    Return venue review context string (Chinese).
    Uses in-memory cache; fetches+summarizes on first call.
    """
    if not force_refresh and venue_id in _venue_cache:
        return _venue_cache[venue_id]["context"]

    venue_info = VENUES.get(venue_id)
    if not venue_info:
        return ""

    # Try fetching each URL until one succeeds
    raw_text = None
    for url in venue_info["urls"]:
        raw_text = _fetch_page_text(url)
        if raw_text and len(raw_text) > 200:
            break

    if not raw_text:
        # Fallback: ask LLM purely from its own knowledge
        raw_text = f"（页面抓取失败，请根据你对 {venue_info['name']} 的了解回答）"

    context = _summarize_venue(venue_id, raw_text, llm_client)
    _venue_cache[venue_id] = {
        "context": context,
        "fetched_at": datetime.utcnow().isoformat(),
    }
    return context
