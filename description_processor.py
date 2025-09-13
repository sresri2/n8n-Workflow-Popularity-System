import spacy
import re

nlp = spacy.load("en_core_web_trf")

def clean_entities(entities):
    keywords = []
    seen = set()
    for ent in entities:
        for part in re.split(r"[&/,]", ent):
            part = part.strip()
            if part and len(part) > 2 and not re.search(r"[@:/.]", part):
                key = part.lower()
                if key not in seen:
                    seen.add(key)
                    keywords.append(part)
    return keywords

def extract_search_terms(description):
    doc = nlp(description)
    entities = [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PRODUCT"]]
    return clean_entities(entities)
