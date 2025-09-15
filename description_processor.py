import spacy
import re

# Load the large transformer-based English NLP model from spaCy.
# This model provides entity recognition for organizations, products, etc.
nlp = spacy.load("en_core_web_trf")

def clean_entities(entities):
    """
    Cleans and deduplicates extracted entity strings.

    Steps:
    1. Splits entities on common delimiters (&, /, ,).
    2. Strips whitespace and removes very short or invalid fragments.
    3. Skips anything containing special characters like @, :, or / (likely usernames/URLs).
    4. Deduplicates terms while preserving order.

    Args:
        entities (list[str]): List of raw entity strings from spaCy.

    Returns:
        list[str]: Cleaned, unique, human-readable keywords.
    """
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
    """
    Processes a text description and extracts relevant search keywords.

    Steps:
    1. Runs spaCy's NLP pipeline on the input text.
    2. Extracts named entities that are either ORG (organizations) or PRODUCT.
    3. Cleans and deduplicates entities using `clean_entities`.

    Args:
        description (str): The raw text (e.g., YouTube transcript, forum post).

    Returns:
        list[str]: List of relevant, cleaned search terms for downstream searches.
    """
    doc = nlp(description)
    entities = [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PRODUCT"]]
    return clean_entities(entities)
