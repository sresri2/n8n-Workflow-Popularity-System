import os
import requests
import json
import re
import time
from collections import Counter
from dotenv import load_dotenv
from description_processor import extract_search_terms
from db_handler import init_db, insert_results

load_dotenv()
DISCOURSE_BASE_URL = "https://community.n8n.io"
CATEGORY_ID = 15
MAX_RESULTS_GENERAL = 10
MAX_RESULTS_SPECIFIC = 10
MAX_TERMS = 20
THROTTLE_SECONDS = 2

EXCLUDE_TERMS = {"n8n", "llm", "chatgpt", "youtube", "zapier", "github", "nadn"}

def normalize_term(term):
    term_clean = term.strip().lower()
    term_clean = re.sub(r'\s+', ' ', term_clean)
    return term_clean.title()

def fetch_category_topics():
    url = f"{DISCOURSE_BASE_URL}/c/built-with-n8n/{CATEGORY_ID}/l/top.json"
    response = requests.get(url)
    response.raise_for_status()
    time.sleep(THROTTLE_SECONDS)
    data = response.json()
    return data.get("topic_list", {}).get("topics", [])

def fetch_topic_details(topic_id):
    url = f"{DISCOURSE_BASE_URL}/t/{topic_id}.json"
    response = requests.get(url)
    response.raise_for_status()
    time.sleep(THROTTLE_SECONDS)
    return response.json()

def collect_initial_topics():
    topics = []
    seen_ids = set()

    raw_topics = fetch_category_topics()
    for topic in raw_topics:
        topic_id = topic["id"]
        if topic_id in seen_ids:
            continue
        seen_ids.add(topic_id)

        try:
            details = fetch_topic_details(topic_id)
            views = details.get("views", 0)
            reply_count = details.get("reply_count", 0)
            like_count = sum(post.get("like_count", 0) for post in details.get("post_stream", {}).get("posts", []))
            unique_contributors = len(set(post.get("username") for post in details.get("post_stream", {}).get("posts", [])))
        except Exception as e:
            print(f"Failed to fetch topic details for {topic_id}: {e}")
            views = reply_count = like_count = unique_contributors = 0

        topics.append({
            "topicId": topic_id,
            "title": topic.get("title", ""),
            "blurb": topic.get("excerpt", ""),
            "reply_count": reply_count,
            "views": views,
            "like_count": like_count,
            "unique_contributors": unique_contributors
        })

    with open("initial_forum_topics.json", "w") as f:
        json.dump(topics, f, indent=2)

    return topics

def extract_search_terms_from_topics(topics):
    all_terms = []
    for topic in topics:
        text = f"{topic['title']} {topic['blurb']}"
        extracted = extract_search_terms(text)
        normalized_terms = [normalize_term(term) for term in extracted if normalize_term(term) not in EXCLUDE_TERMS]
        all_terms.extend(normalized_terms)

    with open("all_forum_extracted_terms.json", "w") as f:
        json.dump(all_terms, f, indent=2)

    term_counts = Counter(all_terms)
    most_common_terms = [term for term, _ in term_counts.most_common(MAX_TERMS)]

    with open("top_forum_extracted_terms.json", "w") as f:
        json.dump(most_common_terms, f, indent=2)

    return most_common_terms

def search_specific_terms_with_topics(terms):
    seen_ids = set()
    topics = []

    for term in terms:
        params = {"q": f"n8n {term} workflow", "include_blurbs": "true"}
        response = requests.get(f"{DISCOURSE_BASE_URL}/search.json", params=params)
        response.raise_for_status()
        time.sleep(THROTTLE_SECONDS)
        results = response.json().get("topics", [])[:MAX_RESULTS_SPECIFIC]

        for topic in results:
            topic_id = topic["id"]
            if topic_id in seen_ids:
                continue
            seen_ids.add(topic_id)

            try:
                details = fetch_topic_details(topic_id)
                views = details.get("views", 0)
                reply_count = details.get("reply_count", 0)
                like_count = sum(post.get("like_count", 0) for post in details.get("post_stream", {}).get("posts", []))
                unique_contributors = len(set(post.get("username") for post in details.get("post_stream", {}).get("posts", [])))
            except Exception as e:
                print(f"Failed to fetch topic details for {topic_id}: {e}")
                views = reply_count = like_count = unique_contributors = 0

            topics.append({
                "topicId": topic_id,
                "title": topic.get("title", ""),
                "blurb": topic.get("blurb", ""),
                "reply_count": reply_count,
                "views": views,
                "like_count": like_count,
                "unique_contributors": unique_contributors
            })

    with open("specific_forum_topic_ids.json", "w") as f:
        json.dump(list(seen_ids), f, indent=2)

    return topics

def build_forum_data(topics):
    forum_data = []
    for topic in topics:
        views = topic.get("views", 0)
        replies = topic.get("reply_count", 0)
        likes = topic.get("like_count", 0)
        contributors = topic.get("unique_contributors", 0)
        forum_data.append({
            "workflow": topic.get("title", ""),
            "platform": "n8n Forum",
            "popularity_metrics": {
                "views": views,
                "replies": replies,
                "likes": likes,
                "unique_contributors": contributors
            }
        })
    return forum_data

def main():
    init_db()
    print("Collecting initial forum topics...")
    initial_topics = collect_initial_topics()

    print("Extracting most popular normalized search terms from forum...")
    top_terms = extract_search_terms_from_topics(initial_topics)

    print("Searching specific forum topics using extracted terms...")
    specific_topics = search_specific_terms_with_topics(top_terms)

    print("Building forum data with popularity metrics...")
    final_data = build_forum_data(specific_topics)

    insert_results("forum", final_data)
    print("Forum results inserted into database.")
    return final_data

if __name__ == "__main__":
    data = main()
