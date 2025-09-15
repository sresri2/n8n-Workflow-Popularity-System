import os
import time
import json
import re
import requests
from collections import Counter
from bs4 import BeautifulSoup
from pytrends.request import TrendReq
from description_processor import extract_search_terms
from db_handler import init_db, insert_results
from dotenv import load_dotenv
load_dotenv()

SERP_API_KEY = os.getenv("SERP_API")
BASE_KEYWORD = "n8n workflows"
TIMEFRAME = "today 3-m"
SLEEP_SECONDS = 10
MAX_TERMS = 2
MAX_SERP_CALLS = 3 
MAX_ARTICLES_PER_TERM = 1
EXCLUDE_TERMS = {"n8n", "llm", "chatgpt", "youtube", "zapier", "github", "nadn"}

def normalize_term(term):
    term_clean = term.strip().lower()
    term_clean = re.sub(r'\s+', ' ', term_clean)
    return term_clean.title()

def serp_search(query, start=0):
    """Fetch search results from SerpAPI."""
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": SERP_API_KEY,
        "start": start,
        "num": 10
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    results = data.get("organic_results", [])
    urls = [r.get("link") for r in results if r.get("link")]
    time.sleep(SLEEP_SECONDS)
    return urls

def fetch_article_text(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return text
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""

def extract_terms_from_search(keyword):
    all_terms = []
    calls_made = 0
    start_index = 0

    while calls_made < MAX_SERP_CALLS:
        try:
            urls = serp_search(keyword, start=start_index)
            if not urls:
                break
            for url in urls[:MAX_ARTICLES_PER_TERM]:
                text = fetch_article_text(url)
                if text:
                    extracted = extract_search_terms(text)
                    normalized = [normalize_term(t) for t in extracted if normalize_term(t) not in EXCLUDE_TERMS]
                    all_terms.extend(normalized)
                    time.sleep(SLEEP_SECONDS)
            calls_made += 1
            start_index += 10
        except Exception as e:
            print(f"Search or article fetch failed: {e}")
            break

    return list(dict.fromkeys(all_terms))

def get_interest_over_time(pytrends, terms):
    interest_data = {}
    for term in terms:
        try:
            pytrends.build_payload([term], cat=0, timeframe=TIMEFRAME, geo="US")
            df = pytrends.interest_over_time()
            if df.empty:
                continue
            series = df[term]
            trend_direction = "stable"
            if len(series) >= 2:
                first = series.iloc[0]
                last = series.iloc[-1]
                if last > first:
                    trend_direction = "up"
                elif last < first:
                    trend_direction = "down"
            interest_data[term] = {
                "avg_interest": float(series.mean()),
                "latest_interest": float(series.iloc[-1]),
                "trend": trend_direction
            }
            time.sleep(SLEEP_SECONDS)
        except Exception as e:
            print(f"Failed to fetch interest for {term}: {e}")
    return interest_data

def main():
    init_db()
    print(f"Performing general search via SerpAPI for '{BASE_KEYWORD}'...")
    extracted_terms = extract_terms_from_search(BASE_KEYWORD)

    term_counts = Counter(extracted_terms)
    top_terms = term_counts

    print("Fetching Google Trends metrics for extracted terms...")
    pytrends = TrendReq(hl="en-US", tz=360)
    interest_data = get_interest_over_time(pytrends, top_terms)

    results = []
    for term in top_terms:
        results.append({
            "term": term,
            "metrics": interest_data.get(term, {
                "avg_interest": None,
                "latest_interest": None,
                "trend": "unknown"
            })
        })

    insert_results("google", results)
    print("Google search results inserted into database.")
    return results

if __name__ == "__main__":
    data = main()
