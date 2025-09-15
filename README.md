# n8n Workflow Popularity System
 
# Project Overview  

This project tracks and ranks trending **n8n workflows** across three sources — **Google search results, YouTube videos, and the official n8n forum** — and exposes the data through a REST API.  

## Data Collection  

The project uses three data collection handlers, each focused on a different source:  

### `google_search_handler.py`  
- Uses **SerpAPI** to scrape Google search results for a general keyword (e.g., `n8n workflows`).  
- Downloads the pages from the search results and processes them using **NLP** (via `description_processor.py`) to extract key workflow-related terms.  
- Performs **follow-up, more specific searches** with these extracted terms (e.g., `google sheets n8n`) and queries **Google Trends** to pull popularity data over time.  
- This lets the system measure interest levels for specific workflows rather than just general mentions.  

### `youtube_handler.py`  
- Searches YouTube for popular n8n-related videos.  
- Downloads and transcribes the video audio using **OpenAI Whisper**.  
- Uses **NLP** to extract key workflow-related terms from the transcripts.  
- Performs **follow-up, more specific YouTube searches** with those terms (e.g., `Slack n8n workflow`) and collects detailed **engagement metrics** such as views, likes, comments, and like/view ratios.  

### `n8n_forum_handler.py`  
- Fetches the top posts from the **Built n8n Workflows** section of the official n8n forum.  
- Extracts key terms using **NLP** and uses them to perform **specific searches inside the forum**.  
- Collects forum-specific metrics such as views, replies, likes, and unique contributor counts to measure discussion activity.  

## Orchestration  

### `main.py`  
- Acts as the **single entry point** for data collection.  
- Calls each handler (Google, YouTube, Forum) in sequence.  
- Collects and deduplicates results, then writes them to the database.  
- Designed to be run as a **daily cron job** so that results stay fresh.  

## Database  

### `db_handler.py`  
- Initializes and manages a SQLite database (`workflow_trends.db`).  
- Atomically replaces existing rows with fresh results on each run, ensuring a full refresh of data.  
- Transactional database updating means API calls and database reads can continue while database is being updated, and the database will never be left completely or partially empty due to the atomic operations on the database. 

## NLP Processing  

### `description_processor.py`  
- Provides reusable functions for text parsing and term extraction.  
- Cleans and normalizes terms before they are used in follow-up searches or stored in the database.  

## API  

### `api.py`  
- A **FastAPI server** that exposes endpoints for retrieving the most popular workflows.  
- Computes a **popularity score** per workflow based on metrics from each source (Google Trends interest, YouTube engagement, or forum activity).  
- Provides endpoints to query data by source (`/google`, `/youtube`, `/forum`) or get a combined view (`/all`).


## Setup & Installation

Follow these steps to install and run the project locally.

### Clone the Repository
```bash
git clone ADD_REPO_NAME
cd REPO_NAME
```
### Create and Activate a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```
### Install Dependencies
```bash
pip install -r requirements.txt
```
### Configure Environment Variables
Create a ```.env``` file in the project root with the following:
```bash
SERP_API=<your_serpapi_key>
YOUTUBE_API_KEY=<your_youtube_api_key>
GOOGLE_CSE_ID=<your_google_custom_search_engine_api_key>
```
### Manual Data Collection (Single run)
```bash
python main.py
```
This runs the three handlers for the three sources of data (Google Search, YouTube, N8N Forum) in sequence and writes results into the SQLite database. 
### Run the API
```bash
uvicorn api:app --reload --port 8000
```
### Set up a Daily Cron Job
Edit your crontab:
```bash
crontab -e
```
Add this line with paths filled in to run ```main.py``` at 02:00 AM every day:
```bash
0 2 * * * /path/to/venv/bin/python /path/to/project/main.py >> /path/to/project/cron.log 2>&1
```

## Architecture & File Structure

This project is organized into clear, modular components to separate concerns and make maintenance easier.  

**File Structure:**

- **main.py** — Single entry point that runs all three handlers  
- **google_search_handler.py** — Handles general and targeted Google searches + Google Trends  
- **youtube_handler.py** — Fetches and processes YouTube videos, extracts key terms, gets engagement metrics  
- **n8n_forum_handler.py** — Fetches and processes n8n forum posts, extracts key terms, gets engagement metrics  
- **description_processor.py** — Central NLP logic for extracting and normalizing terms  
- **db_handler.py** — Initializes and manages SQLite database, atomic insert/replace of results  
- **api.py** — FastAPI app exposing endpoints to retrieve ranked results  
- **workflow_trends.db** — SQLite database (auto-created if missing)  
- **.env** — Stores API keys and secrets  

---

## Data Flow

Here’s how data flows through the system step by step:

1. **Cron Job / Manual Run**  
   - `main.py` is executed (daily via cron job or manually)  
   - It calls the three handlers in sequence  

2. **Data Collection (Handlers)**  
   - **Google**  
     - Runs SerpAPI search → scrapes result pages → extracts key terms  
     - For each term, runs targeted search + Google Trends  
     - Collects average/last interest values & trend direction  
   - **YouTube**  
     - Fetches top n8n videos → transcribes them → extracts terms  
     - Searches again for each term + "n8n"  
     - Collects video metrics (views, likes, comments)  
   - **n8n Forum**  
     - Fetches latest popular posts  
     - Extracts terms from content  
     - Searches forum for each term  
     - Collects metrics (views, replies, contributors)  

3. **NLP & Term Extraction**  
   - `description_processor.py` applies consistent NLP logic to each handler  
   - Ensures extracted terms are normalized and deduplicated  

4. **Database Insert**  
   - Results are inserted into SQLite with `insert_results()`  
   - Existing rows for each source are cleared first to avoid duplicates  

5. **API Access**  
   - `api.py` can be run via Uvicorn to expose endpoints  
   - Each endpoint retrieves data from SQLite, computes popularity scores, sorts, and returns JSON  

6. **Client Consumption**  
   - Any frontend, dashboard, or external client can call `/google`, `/youtube`, `/forum`, or `/all` to fetch the latest ranked results  


## Conclusion

This project provides an end-to-end workflow trends monitoring system for n8n.  
By combining Google search data, YouTube engagement metrics, and n8n forum activity, it gives a comprehensive view of which workflows are currently most relevant and popular.  

- **Automated Data Collection** – Daily cron job ensures the database is always up to date.  
- **Centralized Storage** – All results are stored in SQLite for easy querying and API access.  
- **Unified API** – A single FastAPI service exposes top results from Google Trends, YouTube, and the forum in a standardized JSON format.  

This architecture is designed to be modular and easily extensible. You can add new data sources, tweak scoring weights, or expand the API without changing the core structure.


