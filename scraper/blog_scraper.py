import re
import json
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

KNOWN_GENERIC_AUTHORS = {
    "web author", "youtube channel", "pubmed", "unknown",
    "admin", "editor", "staff", ""
}


def scrape_blog(url):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        res = requests.get(url, verify=False, timeout=10, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        # 1. Author extraction
        author = _extract_author(soup)

        # 2. Published date extraction
        published_date = _extract_date(soup)

        # 3. Page title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # 4. Content extraction (clean, no nav/ads)
        content = _extract_content(soup)

        if len(content.strip()) < 100:
            return None

        return {
            "source_url": url,
            "source_type": "blog",
            "author": author,
            "published_date": published_date,
            "title": title,
            "content": content
        }

    except Exception as e:
        print(f"Blog scrape error [{url}]: {e}")
        return None


def _extract_author(soup):
    """
    Try multiple signals in priority order.
    Cleans Twitter handles and social tags.
    Falls back to 'Web Author' only if nothing found.
    """
    # 1. Standard meta tags
    for attrs in [
        {"name": "author"},
        {"property": "article:author"},
        {"name": "twitter:creator"},
        {"property": "og:author"},
    ]:
        tag = soup.find("meta", attrs)
        if tag and tag.get("content", "").strip():
            raw = tag["content"].strip()
            cleaned = _clean_author(raw)
            if cleaned:
                return cleaned

    # 2. JSON-LD structured data (most reliable on modern blogs)
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                author = entry.get("author", {})
                if isinstance(author, dict):
                    name = author.get("name", "").strip()
                    if name:
                        return _clean_author(name) or name
                elif isinstance(author, list) and author:
                    names = [a.get("name", "") for a in author if isinstance(a, dict)]
                    valid = [_clean_author(n) for n in names if n.strip()]
                    valid = [n for n in valid if n]
                    if valid:
                        return ", ".join(valid)
        except Exception:
            continue

    # 3. Common HTML byline patterns
    for selector in [
        {"class": "author"},
        {"class": "byline"},
        {"rel": "author"},
        {"itemprop": "author"},
        {"class": "post-author"},
        {"class": "entry-author"},
    ]:
        tag = soup.find(attrs=selector)
        if tag:
            text = tag.get_text(strip=True)
            if text and len(text) < 80:
                cleaned = _clean_author(text)
                if cleaned:
                    return cleaned

    return "Web Author"


def _clean_author(name):
    """
    Remove Twitter handles (@username), URLs, and social prefixes.
    Returns cleaned name or empty string if it looks fake/generic.
    """
    if not name:
        return ""

    # Remove Twitter/social handles like @Simplilearn
    name = re.sub(r'^@+', '', name).strip()

    # Remove URLs
    name = re.sub(r'https?://\S+', '', name).strip()

    # Remove "By " prefix
    name = re.sub(r'^[Bb]y\s+', '', name).strip()

    # If result is generic, return empty so fallback continues
    if name.lower() in KNOWN_GENERIC_AUTHORS:
        return ""

    # Sanity check: too short or all digits = not a real name
    if len(name) < 2 or name.isdigit():
        return ""

    return name


def _extract_date(soup):
    """
    Try meta tags, JSON-LD, then common time/span elements.
    """
    # 1. Meta tags
    for attrs in [
        {"property": "article:published_time"},
        {"name": "date"},
        {"name": "pubdate"},
        {"itemprop": "datePublished"},
        {"property": "og:published_time"},
    ]:
        tag = soup.find("meta", attrs)
        if tag and tag.get("content", "").strip():
            return tag["content"].strip()[:10]

    # 2. JSON-LD
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                for field in ("datePublished", "dateCreated", "dateModified"):
                    val = entry.get(field, "")
                    if val:
                        return str(val)[:10]
        except Exception:
            continue

    # 3. HTML time elements
    time_tag = soup.find("time")
    if time_tag:
        dt = time_tag.get("datetime", "") or time_tag.get_text(strip=True)
        if dt:
            return dt[:10]

    return "Unknown"


def _extract_content(soup):
    """
    Remove boilerplate elements, then extract paragraph text.
    """
    # Remove noise elements
    for tag in soup(["nav", "header", "footer", "aside", "script",
                     "style", "form", "noscript", "iframe",
                     "figure", "figcaption", "advertisement"]):
        tag.decompose()

    # Remove elements with ad/nav class hints
    for tag in soup.find_all(True, {"class": [
        "ad", "ads", "advertisement", "sidebar", "nav",
        "menu", "cookie", "popup", "newsletter", "related"
    ]}):
        tag.decompose()

    # Try to find the main article body first
    article = (
        soup.find("article") or
        soup.find("main") or
        soup.find(attrs={"class": "post-content"}) or
        soup.find(attrs={"class": "entry-content"}) or
        soup.find(attrs={"class": "article-body"}) or
        soup.find(attrs={"itemprop": "articleBody"}) or
        soup.body
    )

    if article is None:
        return ""

    paragraphs = article.find_all("p")
    content = " ".join([
        p.get_text(strip=True)
        for p in paragraphs
        if len(p.get_text(strip=True)) > 40
    ])

    return content