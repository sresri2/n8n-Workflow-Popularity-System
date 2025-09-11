import spacy
import re

nlp = spacy.load("en_core_web_sm")

def clean_entities(entities):
    keywords = []
    for ent in entities:
        for part in re.split(r"[&/,]", ent):
            part = part.strip()
            if part and len(part) > 2:
                keywords.append(part)
    return keywords

def extract_search_terms(description):
    doc = nlp(description)

    entities = [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PRODUCT", "WORK_OF_ART"]]

    res = clean_entities(entities)
    return res
