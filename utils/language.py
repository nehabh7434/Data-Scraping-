def detect_language(text):
    try:
        from langdetect import detect
        return detect(text)
    except:
        return "unknown"