import spacy
from collections import Counter
from langdetect import detect

nlp = spacy.load("en_core_web_sm")

def extract_tags(text):
    doc = nlp(text)

    nouns = [token.text.lower() for token in doc if token.pos_ == "NOUN"]
    entities = [ent.text.lower() for ent in doc.ents]

    common = Counter(nouns + entities).most_common(5)
    tags = [word for word, _ in common]

    return tags


def detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"