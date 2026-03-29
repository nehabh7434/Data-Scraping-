from youtube_transcript_api import YouTubeTranscriptApi


def scrape_youtube(video_id):
    try:
        # New API syntax (v0.6.0+)
        ytt = YouTubeTranscriptApi()
        fetched = ytt.fetch(video_id)
        text = " ".join([t.text for t in fetched])
    except Exception as e:
        print(f"Transcript fetch failed for {video_id}: {e}")
        text = "Transcript not available"

    return {
        "source_url":     f"https://youtube.com/watch?v={video_id}",
        "source_type":    "youtube",
        "author":         "YouTube Channel",
        "published_date": "Unknown",
        "content":        text,
    }