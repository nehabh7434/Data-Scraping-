# Data Scraping & Trust Scoring Pipeline

A multi-source web scraper that collects structured content from blogs, YouTube, and PubMed, and evaluates each source using a trust scoring algorithm.

---

## Project Structure

```
project/
├── scraper/
│   ├── blog_scraper.py       # Scrapes blog articles
│   ├── youtube_scraper.py    # Extracts YouTube transcripts
│   └── pubmed_scraper.py     # Fetches PubMed articles via API
├── scoring/
│   └── trust_score.py        # Trust score algorithm (5 factors)
├── utils/
│   ├── tagging.py            # Auto topic tagging using spaCy
│   ├── chunking.py           # Splits content into chunks
│   └── language.py           # Language detection using langdetect
├── output/
│   └── final_output.json     # Generated output (6 sources)
├── main.py                   # Pipeline entry point
├── README.md
└── .gitignore
```

---

## Tools & Libraries

| Library | Purpose |
|---|---|
| `requests` | HTTP requests for blog and PubMed scraping |
| `beautifulsoup4` | HTML parsing and content extraction |
| `youtube-transcript-api` | YouTube transcript extraction |
| `spacy` (en_core_web_sm) | NLP for topic tagging |
| `langdetect` | Automatic language detection |
| `lxml` / `xml.etree` | PubMed XML parsing |

---

## How to Run

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install requests beautifulsoup4 youtube-transcript-api spacy langdetect
python -m spacy download en_core_web_sm

# 3. Run the pipeline
python main.py
```

Output is saved to `output/final_output.json`.

---

## Scraping Approach

### Blogs
- Uses `requests` + `BeautifulSoup`
- Removes noise elements: nav, footer, ads, sidebars
- Extracts author via meta tags → JSON-LD → HTML byline (priority order)
- Extracts date via `article:published_time` → JSON-LD → `<time>` tag
- Falls back gracefully if any field is missing

### YouTube
- Uses `youtube-transcript-api` to pull auto-generated transcripts
- If transcript unavailable, content is set to "Transcript not available"
- Trust scorer applies a penalty for missing transcripts
- No API key required

### PubMed
- Calls the free Entrez XML API with a PMID
- Extracts: title, abstract, all authors, journal, publication date
- Citation count fetched from Semantic Scholar free API as fallback
- No API key required for either service

---

## Trust Score Design

```
Trust Score = author_credibility + citation_count + domain_authority
            + recency + medical_disclaimer_presence + source_and_content
```

Each factor is weighted independently and the final score is capped between 0.0 and 1.0. A full breakdown per factor is stored in `trust_score_breakdown` inside each output entry.

## Trust Scoring Factors

| Factor | Max | Key Logic |
|--------|-----|----------|
| Author Credibility | 0.20 | Named person > organization > generic placeholder |
| Citation Count | 0.20 | From API or inferred via DOI/references in content |
| Domain Authority | 0.25 | Static lookup + bonuses for .edu / .gov domains |
| Recency | 0.20 | Full score ≤1 year, decreases over time, penalty for old medical content |
| Medical Disclaimer | +0.15 / -0.10 | Applied only if ≥3 medical keywords are present |
| Source & Content Quality | ~0.20 | +0.15 (PubMed), +0.08 (blog/YouTube), +0.05 (>3000 chars), +0.03 (>1000 chars), +0.02 (language detected), −0.05 (short content), −0.05 (missing YouTube transcript) |
---

## Edge Cases Handled

- **Missing author** → credibility score = 0, pipeline continues
- **Multiple authors** (PubMed) → scores averaged across all authors
- **Missing publish date** → recency = 0, field set to "Unknown"
- **Non-English / short content** → language set to "unknown" instead of guessing
- **Twitter handle as author** (e.g. @Simplilearn) → @ prefix stripped automatically
- **JavaScript-rendered pages** → content < 100 chars, entry skipped with warning
- **Transcript unavailable** → content penalty applied, language set to "unknown"

---

## Abuse Prevention

- **Fake authors** - generic names (Web Author, admin, staff) score 0 credibility
- **SEO spam** — spam keywords in URL path set domain authority to 0
- **Misleading medical content** — sources discussing medical topics without a disclaimer receive -0.10 penalty
- **Outdated medical info** — articles >3 years old on medical topics get extra recency penalty

---

## Limitations

- JavaScript-rendered sites (OpenAI, DeepLearning.ai) cannot be scraped without a headless browser like Playwright
- YouTube transcripts may be blocked in some network environments — scores of 0.08 for those videos are expected and correct
- Domain authority uses a static lookup table, not a live API (Moz/Ahrefs are paid services)
- Citation count relies on Semantic Scholar search matching — may return 0 if title match fails
- Topic tagging uses noun frequency (spaCy) rather than semantic keyword extraction

---


## Results & Analysis

| Source | Trust Score | Main Factor |
|--------|------------|-------------|
| IBM – Machine Learning | 0.56 | High domain authority + strong recency + valid author |
| GeeksforGeeks – ML | 0.58 | Good recency + decent content quality |
| IBM – Neural Networks | 0.66 | High domain authority + strong recency |
| YouTube #1 | 0.25 | Low metadata + weak structured content |
| YouTube #2 | 0.25 | Missing metadata + partial transcript |
| PubMed Article | 0.65 | High domain authority + multiple authors |