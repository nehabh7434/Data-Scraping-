from datetime import datetime
from urllib.parse import urlparse

# Domain authority lookup (rule-based)
TRUSTED_DOMAINS = {
    "pubmed.ncbi.nlm.nih.gov": 1.0,
    "nih.gov": 1.0,
    "who.int": 1.0,
    "nature.com": 0.95,
    "ibm.com": 0.85,
    "harvard.edu": 0.95,
    "mit.edu": 0.95,
    "datacamp.com": 0.65,
    "geeksforgeeks.org": 0.60,
    "simplilearn.com": 0.60,
    "machinelearningmastery.com": 0.65,
    "medium.com": 0.45,
    "wordpress.com": 0.30,
    "blogspot.com": 0.25,
}

SPAM_SIGNALS = ["free-traffic", "seo-hack", "click-here", "buy-now"]

MEDICAL_KEYWORDS = [
    "treatment", "diagnosis", "symptoms", "disease", "medicine",
    "therapy", "clinical", "patient", "drug", "dose", "health"
]

DISCLAIMER_PHRASES = [
    "consult a doctor", "not medical advice", "consult your physician",
    "seek professional advice", "medical disclaimer", "not a substitute"
]

KNOWN_GENERIC_AUTHORS = {
    "web author", "youtube channel", "pubmed", "unknown",
    "admin", "editor", "staff", ""
}


# Factor 1: Author Credibility  (0.0 – 0.20)

def score_author_credibility(item):
    author_raw = item.get("author", "").strip()
    if not author_raw or author_raw.lower() in KNOWN_GENERIC_AUTHORS:
        return 0.0

    # Multiple authors: split and average
    separators = [";", ",", " and "]
    authors = [author_raw]
    for sep in separators:
        if sep in author_raw:
            authors = [a.strip() for a in author_raw.replace(" and ", ",").split(",")]
            break

    def single_author_score(name):
        name_lower = name.lower()
        score = 0.10  # base: named author exists
        if any(c in name_lower for c in ["phd", "md", "dr.", "prof.", "professor"]):
            score += 0.05
        if name.isupper() or len(name.split()) == 1 and len(name) > 6:
            score += 0.03
        if len(name.split()) == 1 and len(name) < 4:
            score -= 0.05
        return max(0.0, min(score, 0.20))

    return round(sum(single_author_score(a) for a in authors) / len(authors), 3)


# Factor 2: Citation Count  (0.0 – 0.20)

def score_citation_count(item):
    citations = item.get("citation_count", None)
    if citations is not None:
        try:
            c = int(citations)
            if c >= 100: return 0.20
            if c >= 50:  return 0.15
            if c >= 10:  return 0.10
            if c >= 1:   return 0.05
        except (ValueError, TypeError):
            pass

    # Fallback: infer from content
    content = item.get("content", "").lower()
    doi_count = content.count("doi:")
    ref_count = content.count("references") + content.count("bibliography")
    if doi_count >= 5 or ref_count >= 2:
        return 0.10
    if doi_count >= 1:
        return 0.05
    return 0.0



# Factor 3: Domain Authority  (0.0 – 0.25)

def score_domain_authority(item):
    url = item.get("source_url", "")
    if not url:
        return 0.0

    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return 0.0

    path = urlparse(url).path.lower()
    if any(spam in path for spam in SPAM_SIGNALS):
        return 0.0

    if domain in TRUSTED_DOMAINS:
        return round(TRUSTED_DOMAINS[domain] * 0.25, 3)

    for trusted, da in TRUSTED_DOMAINS.items():
        if domain.endswith("." + trusted):
            return round(da * 0.25, 3)

    if domain.endswith(".edu"):  return 0.18
    if domain.endswith(".gov"):  return 0.20
    if domain.endswith(".org"):  return 0.12
    if "youtube.com" in domain:  return 0.10

    return 0.08


# Factor 4: Recency  (0.0 – 0.20)

def score_recency(item):
    date_str = item.get("published_date", "").strip()
    if not date_str or date_str.lower() in ("unknown", "n/a", ""):
        return 0.0

    formats = ["%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y", "%Y"]
    parsed = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return 0.0

    age_years = (datetime.now() - parsed).days / 365.25
    content = item.get("content", "").lower()
    is_medical = sum(1 for kw in MEDICAL_KEYWORDS if kw in content) >= 3

    if age_years <= 1:    base = 0.20
    elif age_years <= 2:  base = 0.15
    elif age_years <= 3:  base = 0.10
    elif age_years <= 5:  base = 0.05
    else:                 base = 0.0

    if is_medical and age_years > 3:
        base = max(0.0, base - 0.10)

    return round(base, 3)



# Factor 5: Medical Disclaimer  (0.0 – 0.15)

def score_medical_disclaimer(item):
    content = item.get("content", "").lower()

    # Require at least 3 medical keywords to count as medical content
    # Prevents general tech articles from being penalised for brief mentions
    medical_hit_count = sum(1 for kw in MEDICAL_KEYWORDS if kw in content)
    is_medical = medical_hit_count >= 3

    if not is_medical:
        return 0.0

    has_disclaimer = any(phrase in content for phrase in DISCLAIMER_PHRASES)

    if has_disclaimer:
        return 0.15
    else:
        return -0.10



# Factor 6: Source type + content quality (bonus)

def score_source_and_content(item):
    score = 0.0
    source_type = item.get("source_type", "")
    content = item.get("content", "")
    content_len = len(content)

    if source_type == "pubmed":    score += 0.15
    elif source_type == "youtube": score += 0.08
    elif source_type == "blog":    score += 0.08

    if content_len > 3000:   score += 0.05
    elif content_len > 1000: score += 0.03
    elif content_len < 100:  score -= 0.05

    if source_type == "youtube" and "transcript not available" in content.lower():
        score -= 0.05

    lang = item.get("language", "unknown")
    if lang not in ("unknown", ""):
        score += 0.02

    return round(score, 3)


# MAIN: compute_trust_score

def compute_trust_score(item):
    """
    Trust Score = f(
        author_credibility,
        citation_count,
        domain_authority,
        recency,
        medical_disclaimer_presence
    )
    Range: 0.0 – 1.0
    """
    author_score     = score_author_credibility(item)
    citation_score   = score_citation_count(item)
    domain_score     = score_domain_authority(item)
    recency_score    = score_recency(item)
    disclaimer_score = score_medical_disclaimer(item)
    content_score    = score_source_and_content(item)

    total = (
        author_score +
        citation_score +
        domain_score +
        recency_score +
        disclaimer_score +
        content_score
    )

    final = round(min(max(total, 0.0), 1.0), 2)

    item["trust_score_breakdown"] = {
        "author_credibility":  author_score,
        "citation_count":      citation_score,
        "domain_authority":    domain_score,
        "recency":             recency_score,
        "medical_disclaimer":  disclaimer_score,
        "source_and_content":  content_score,
        "final":               final
    }

    return final