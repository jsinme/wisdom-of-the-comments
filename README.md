# wisdom-of-the-comments

Scripts to scrape, filter, and analyze the comments on YouTube videos. Made to assist in the background research for an upcoming video by [KatzVE](https://www.youtube.com/@KatzVE).

## Setup

Requires the following API key set as an environment variable.

**`YOUTUBE_API_KEY`**: a YouTube Data API v3 key from a Google Cloud Project. Create a new project, enable the API, and create a new credential scoped only to that API.

Requires python 3.10+. `uv run` handles it automatically.

## Usage

Pass in an 11-character Youtube video ID:

```sh
uv run scripts/fetch_comments.py "VIDEO_ID"
```

**`fetch_comments.py`** writes to `data/<title-slug>-<id>.comments.jsonl` by default. It outputs one json object per public comment per line. It records all threads in newest first order with nested replies directly under each top level comment in oldest first order (same as how you'd see it in the comments section sorting by newest).

## Data

`data/` is gitignored. Only public comments are scraped but commenter names and channel IDs could be considered PII so just leaving it out by default to respect people's privacy and right to delete comments and not have them saved here.
