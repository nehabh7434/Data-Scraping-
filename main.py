import json

from scraper.blog_scraper import scrape_blog
from scraper.youtube_scraper import scrape_youtube
from scraper.pubmed_scraper import scrape_pubmed

from utils.language import detect_language
from utils.tagging import extract_tags
from utils.chunking import chunk_text
from scoring.trust_score import compute_trust_score



# INPUT SOURCES


blogs = [
    "https://www.ibm.com/topics/machine-learning",
    "https://www.geeksforgeeks.org/machine-learning/",
    "https://www.ibm.com/topics/neural-networks",  # try this
]

videos = [
    "Gv9_4yMHFhI",
    "HcqpanDadyQ",
]

pubmed_ids = [
    "37126756",
]



# MAIN PIPELINE


data = []

# -------- BLOGS --------
for url in blogs:
    item = scrape_blog(url)

    if item is None:
        print(f"Skipped blog: {url}")
        continue

    try:
        item["language"] = detect_language(item["content"])
        item["topic_tags"] = extract_tags(item["content"])
        item["content_chunks"] = chunk_text(item["content"])
        item["region"] = "global"
        item["trust_score"] = compute_trust_score(item)
    except Exception as e:
        print(f"Error processing blog {url}: {e}")
        continue

    data.append(item)


# -------- YOUTUBE --------
for vid in videos:
    item = scrape_youtube(vid)

    if item is None:
        print(f"Skipped video: {vid}")
        continue

    try:
        # Skip language detection if transcript failed
        # langdetect gives wrong results on very short strings
        if "transcript not available" in item["content"].lower():
            item["language"] = "unknown"
        else:
            item["language"] = detect_language(item["content"])

        item["topic_tags"] = extract_tags(item["content"])
        item["content_chunks"] = chunk_text(item["content"])
        item["region"] = "global"
        item["trust_score"] = compute_trust_score(item)
    except Exception as e:
        print(f"Error processing video {vid}: {e}")
        continue

    data.append(item)


# -------- PUBMED --------
for pid in pubmed_ids:
    item = scrape_pubmed(pid)

    if item is None:
        print(f"Skipped pubmed: {pid}")
        continue

    try:
        item["language"] = detect_language(item["content"])
        item["topic_tags"] = extract_tags(item["content"])
        item["content_chunks"] = chunk_text(item["content"])
        item["region"] = "global"
        item["trust_score"] = compute_trust_score(item)
    except Exception as e:
        print(f"Error processing pubmed {pid}: {e}")
        continue

    data.append(item)



# SAVE OUTPUT


with open("output/final_output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("\n Pipeline completed successfully!")
print(f"Total valid entries: {len(data)}")