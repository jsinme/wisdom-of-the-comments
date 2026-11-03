# /// script
# requires-python = ">=3.10"
# ///

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.googleapis.com/youtube/v3"
REPO = Path(__file__).resolve().parent.parent


def get_key() -> str:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("error: set YOUTUBE_API_KEY in the environment")
    return key


def call_api(resource: str, params: dict, key: str):
    url = f"{API}/{resource}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-Goog-Api-Key": key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def call_api_multipage(resource: str, params: dict, key: str):
    token = None
    while True:
        page = call_api(
            resource, {**params, **({"pageToken": token} if token else {})}, key
        )
        yield page
        token = page.get("nextPageToken")
        if not token:
            return


def get_video_details(vid: str, key: str):
    params = {"part": "snippet,statistics", "id": vid}
    videos = call_api("videos", params, key)["items"]
    if not videos:
        raise SystemExit("error: video not found")
    title = videos[0]["snippet"]["title"]
    channel_id = videos[0]["snippet"]["channelId"]
    reported_comment_count = int(videos[0]["statistics"].get("commentCount", 0))

    return title, channel_id, reported_comment_count


def slug(title: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:limit].rstrip("-") or "video"


def make_record(comment: dict, channel_id: str, total_reply_count: int | None = None):
    snippet = comment["snippet"]
    author_channel_id = (snippet.get("authorChannelId") or {}).get("value")
    record = {
        "id": comment["id"],
        "parent_id": snippet.get("parentId"),
        "is_creator": author_channel_id is not None and author_channel_id == channel_id,
        "text": snippet.get("textOriginal", snippet.get("textDisplay")),
        "like_count": snippet.get("likeCount"),
        "published_at": snippet.get("publishedAt"),
        "updated_at": snippet.get("updatedAt"),
    }
    if total_reply_count is not None:
        record["total_reply_count"] = total_reply_count
    record["snippet"] = snippet
    return record


def main():
    key = get_key()

    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("-o", "--out", type=Path)
    args = ap.parse_args()

    vid = args.video

    title, channel_id, reported_comment_count = get_video_details(vid, key)
    if reported_comment_count == 0:
        raise SystemExit("error: video has no comments")

    print(f"Youtube reports {reported_comment_count} comments")

    out = args.out or REPO / "data" / f"{slug(title)}-{vid}.comments.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    tmp = out.with_name(out.name + ".part")
    with tmp.open("w", encoding="utf-8") as f:
        thread_params = {
            "part": "snippet,replies",
            "videoId": vid,
            "maxResults": 100,
            "order": "time",
            "textFormat": "plainText",
        }
        for thread_page in call_api_multipage("commentThreads", thread_params, key):
            for thread in thread_page.get("items", []):
                top = thread["snippet"]["topLevelComment"]
                if top["id"] in seen:
                    continue
                seen.add(top["id"])
                reply_count = thread["snippet"].get("totalReplyCount", 0)
                replies = thread.get("replies", {}).get("comments", [])
                if len(replies) < reply_count:
                    reply_params = {
                        "part": "snippet",
                        "parentId": top["id"],
                        "maxResults": 100,
                        "textFormat": "plainText",
                    }
                    replies = [
                        reply
                        for page in call_api_multipage("comments", reply_params, key)
                        for reply in page.get("items", [])
                    ]
                replies = [reply for reply in replies if reply["id"] not in seen]
                seen.update(reply["id"] for reply in replies)

                f.write(
                    json.dumps(
                        make_record(top, channel_id, reply_count),
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                for reply in sorted(
                    replies, key=lambda reply: reply["snippet"].get("publishedAt", "")
                ):
                    f.write(
                        json.dumps(make_record(reply, channel_id), ensure_ascii=False)
                        + "\n"
                    )
    tmp.replace(out)

    print(f"{len(seen)} comments recorded at {out}")


if __name__ == "__main__":
    main()
