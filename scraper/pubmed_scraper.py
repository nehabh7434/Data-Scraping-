import requests
import xml.etree.ElementTree as ET


def scrape_pubmed(pmid):
    try:
        url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            f"?db=pubmed&id={pmid}&retmode=xml"
        )
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        root = ET.fromstring(res.content)

        # 1. Title
        title_el = root.find(".//ArticleTitle")
        title = title_el.text.strip() if title_el is not None else ""

        # 2. Abstract
        abstract_el = root.find(".//AbstractText")
        abstract = abstract_el.text.strip() if abstract_el is not None else ""

        # 3. Authors (multiple authors supported)
        authors = _extract_authors(root)

        # 4. Journal
        journal_el = root.find(".//Journal/Title")
        journal = journal_el.text.strip() if journal_el is not None else ""

        # 5. Published date
        published_date = _extract_pubmed_date(root)

        # 6. Citation count — try PubMed XML first, then Semantic Scholar
        citation_count = _get_citation_count(root, title)

        # 7. Build content string
        content = f"{title} {abstract}".strip()

        if not content:
            return None

        return {
            "source_url":       f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
            "source_type":      "pubmed",
            "author":           authors,
            "published_date":   published_date,
            "title":            title,
            "journal":          journal,
            "content":          content,
            "citation_count":   citation_count,
        }

    except Exception as e:
        print(f"PubMed scrape error [PMID {pmid}]: {e}")
        return None


def _extract_authors(root):
    """
    Extract all authors and join them.
    Edge case: no authors → 'Unknown'
    Multiple authors → 'Last1 F1, Last2 F2, ...'
    """
    author_list = root.findall(".//AuthorList/Author")
    if not author_list:
        return "Unknown"

    names = []
    for author in author_list:
        last = author.find("LastName")
        fore = author.find("ForeName") or author.find("Initials")
        if last is not None:
            name = last.text.strip()
            if fore is not None and fore.text:
                name += f" {fore.text.strip()}"
            names.append(name)

    # Collective author fallback
    if not names:
        collective = root.find(".//AuthorList/Author/CollectiveName")
        if collective is not None:
            return collective.text.strip()

    return ", ".join(names) if names else "Unknown"


def _extract_pubmed_date(root):
    """
    Try ArticleDate first (electronic pub date),
    then PubDate (print date).
    Edge case: missing → 'Unknown'
    """
    # Electronic publication date
    article_date = root.find(".//ArticleDate")
    if article_date is not None:
        year  = article_date.findtext("Year", "")
        month = article_date.findtext("Month", "01")
        day   = article_date.findtext("Day", "01")
        if year:
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Print publication date
    pub_date = root.find(".//PubDate")
    if pub_date is not None:
        year  = pub_date.findtext("Year", "")
        month = pub_date.findtext("Month", "01")
        day   = pub_date.findtext("Day", "01")

        month_map = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
        }
        month = month_map.get(month, month.zfill(2) if month.isdigit() else "01")

        if year:
            return f"{year}-{month}-{day.zfill(2) if day.isdigit() else '01'}"

    return "Unknown"


def _get_citation_count(root, title):
    """
    Try PubMed XML field first.
    Fall back to Semantic Scholar free API (no key needed).
    Returns citation count as string.
    """
    # 1. Try PubMed XML
    citation_el = root.find(".//MedlineCitation/NumberOfReferences")
    if citation_el is not None and citation_el.text:
        count = citation_el.text.strip()
        if count.isdigit() and int(count) > 0:
            return count

    
    try:
        ss_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": title,
            "fields": "citationCount",
            "limit": 1
        }
        res = requests.get(ss_url, params=params, timeout=8)
        data = res.json()
        count = data["data"][0]["citationCount"]
        return str(count)
    except Exception:
        pass

    return "0"