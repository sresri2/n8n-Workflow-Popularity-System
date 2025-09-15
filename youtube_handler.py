import os
import requests
import json
import re
import time
import subprocess
from collections import Counter
from dotenv import load_dotenv
from description_processor import extract_search_terms
import torch
import whisper
from db_handler import init_db, insert_results

def load_whisper_model(model_size="small"):
    model = whisper.load_model(model_size)
    try:
        if torch.backends.mps.is_available():
            model = model.to("mps")
            _ = torch.zeros(1, device="mps")
            print("Running Whisper on MPS (Apple Silicon GPU)")
        else:
            print("Running Whisper on CPU")
    except NotImplementedError:
        print("MPS not fully supported, falling back to CPU")
        model = model.to("cpu")
    return model

WHISPER_MODEL = load_whisper_model("tiny")

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE_URL = "https://www.googleapis.com/youtube/v3"

MAX_RESULTS_GENERAL = 3
MAX_RESULTS_SPECIFIC = 3
MAX_GENERAL_SEARCHES = 2
MAX_TERMS = 5
THROTTLE_SECONDS = 2


def normalize_term(term):
    term_clean = term.strip().lower()
    term_clean = re.sub(r'\s+', ' ', term_clean)
    return term_clean.title()

def search_youtube(query, max_results=5, order="viewCount"):
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": order,
        "key": API_KEY,
    }
    response = requests.get(f"{BASE_URL}/search", params=params)
    response.raise_for_status()
    time.sleep(THROTTLE_SECONDS)
    return response.json().get("items", [])

def get_video_details(video_ids):
    if not video_ids:
        return []
    params = {
        "part": "statistics,snippet",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }
    response = requests.get(f"{BASE_URL}/videos", params=params)
    response.raise_for_status()
    time.sleep(THROTTLE_SECONDS)
    return response.json().get("items", [])

def collect_initial_videos():
    search_terms = [
        "Best n8n workflows",
        "Most useful n8n workflows",
        "Popular n8n automations"
    ][:MAX_GENERAL_SEARCHES]

    videos = []
    seen_ids = set()

    for term in search_terms:
        print(f"Searching for: {term}")
        search_results = search_youtube(term, max_results=MAX_RESULTS_GENERAL)
        video_ids = [item["id"]["videoId"] for item in search_results if item["id"]["videoId"] not in seen_ids]

        if not video_ids:
            continue

        details = get_video_details(video_ids)

        for video in details:
            vid = video["id"]
            seen_ids.add(vid)
            videos.append({
                "videoId": vid,
                "title": video["snippet"]["title"],
                "description": video["snippet"]["description"],
            })

    with open("initial_videos.json", "w") as f:
        json.dump(videos, f, indent=2)

    return videos

def extract_search_terms_from_videos(videos):
    all_terms = []
    filter_out = [normalize_term(t) for t in [
        "n8n", "chatgpt", "llm", "youtube", "zapier", "make", "pabbly", "ifttt", "nadn", "github"
    ]]

    for video in videos:
        vid = video["videoId"]
        print(f"Transcribing initial video {vid} with Whisper...")
        try:
            text = transcribe_with_whisper(vid)
            time.sleep(THROTTLE_SECONDS)
            if text.strip():
                extracted = extract_search_terms(text)
                normalized_terms = [normalize_term(term) for term in extracted]
                filtered_terms = [t for t in normalized_terms if t not in filter_out]
                all_terms.extend(filtered_terms)
                print(f"Transcript terms for {vid}: {filtered_terms}")
            else:
                print(f"No speech detected for {vid}")
        except Exception as e:
            print(f"Transcription failed for {vid}: {e}")

    with open("all_extracted_terms.json", "w") as f:
        json.dump(all_terms, f, indent=2)

    term_counts = Counter(all_terms)
    most_common_terms = [term for term, _ in term_counts.most_common(MAX_TERMS)]

    with open("top_extracted_terms.json", "w") as f:
        json.dump(most_common_terms, f, indent=2)

    return most_common_terms

def download_audio(video_id):
    filename = f"{video_id}.mp3"
    try:
        subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "-x", "--audio-format", "mp3", "-o", filename, f"https://www.youtube.com/watch?v={video_id}"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return filename
    except Exception as e:
        print(f"Failed to download audio for {video_id}: {e}")
        return None

def transcribe_with_whisper(video_id):
    filename = download_audio(video_id)
    if not filename:
        return ""
    try:
        result = WHISPER_MODEL.transcribe(filename)
        return result["text"]
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def search_specific_terms_with_transcripts(terms):
    seen_ids = set()

    for term in terms:
        query = f"n8n {term} workflow"
        results = search_youtube(query, max_results=MAX_RESULTS_SPECIFIC, order="relevance")
        for item in results:
            vid = item["id"]["videoId"]
            if vid in seen_ids:
                continue
            seen_ids.add(vid)

            try:
                print(f"Transcribing video {vid} with Whisper...")
                text = transcribe_with_whisper(vid)
                time.sleep(THROTTLE_SECONDS)
                if text.strip():
                    extracted_terms = extract_search_terms(text)
                    normalized_terms = [normalize_term(term) for term in extracted_terms]
                    print(f"Transcript terms for {vid}: {normalized_terms}")
                else:
                    print(f"No speech detected for {vid}")
            except Exception as e:
                print(f"Transcription failed for {vid}: {e}")

    with open("specific_video_ids.json", "w") as f:
        json.dump(list(seen_ids), f, indent=2)

    return list(seen_ids)

def build_video_data(video_ids):
    video_data = []
    details = get_video_details(video_ids)
    for video in details:
        stats = video["statistics"]
        title = video["snippet"]["title"]
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0)) if "likeCount" in stats else 0
        comments = int(stats.get("commentCount", 0)) if "commentCount" in stats else 0
        like_ratio = likes / views if views > 0 else 0
        comment_ratio = comments / views if views > 0 else 0
        video_data.append({
            "workflow": title,
            "platform": "YouTube",
            "popularity_metrics": {
                "views": views,
                "likes": likes,
                "comments": comments,
                "like_to_view_ratio": like_ratio,
                "comment_to_view_ratio": comment_ratio,
            }
        })
    return video_data

def main():
    init_db()
    print("Collecting initial search results...")
    initial_videos = collect_initial_videos()

    print("Extracting most popular normalized search terms...")
    top_terms = extract_search_terms_from_videos(initial_videos)

    print("Searching specific terms and processing transcripts...")
    specific_video_ids = search_specific_terms_with_transcripts(top_terms)

    print("Fetching video statistics...")
    final_data = build_video_data(specific_video_ids)

    insert_results("youtube", final_data)
    print("YouTube results inserted into database.")
    return final_data

if __name__ == "__main__":
    data = main()
