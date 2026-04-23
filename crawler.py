import os
from googleapiclient.discovery import build  # Google API client library

# ============================================================
# REPLACE THIS WITH YOUR YOUTUBE API KEY
# How to get it: console.cloud.google.com → New Project →
# Enable "YouTube Data API v3" → Credentials → Create API Key
# ============================================================
YOUTUBE_API_KEY = "API"

def search_youtube(query, max_results=10):
    """
    Searches YouTube for videos matching a query.
    Returns list of video info dicts.
    """
    try:
        # build() creates a YouTube API client using your key
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        # .search().list() is the YouTube API call for searching
        request = youtube.search().list(
            part="snippet",           # "snippet" gives us title, description, channel
            q=query,                  # search query
            type="video",             # only videos, not playlists or channels
            maxResults=max_results,   # how many results to return
            order="date"              # newest first
        )

        response = request.execute()  # Actually make the API call

        videos = []
        # response["items"] is the list of search results
        for item in response.get("items", []):
            video_id = item["id"]["videoId"]  # YouTube video ID like "dQw4w9WgXcQ"
            snippet = item["snippet"]          # Contains title, description, etc.

            videos.append({
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", "")
            })

        return videos

    except Exception as e:
        print(f"YouTube search error: {e}")
        return []

def build_search_queries(owner_name, original_filename):
    """
    Creates smart search queries based on owner info and filename.
    Multiple queries = better chance of finding stolen copies.
    """
    # Remove file extension from filename for cleaner search
    clean_name = os.path.splitext(original_filename)[0]  # "match_clip.mp4" → "match_clip"
    clean_name = clean_name.replace("_", " ").replace("-", " ")  # underscores to spaces

    queries = [
        f"{owner_name} sports clip",           # owner's name + sports clip
        f"{clean_name} sports highlights",     # filename as search term
        f"{owner_name} {clean_name}",          # both combined
    ]
    return queries

def score_suspicion(video_info, owner_name):
    """
    Gives a suspicion score to a found video.
    Higher score = more likely to be stolen.
    Returns 0-100.
    """
    score = 30  # Start with base score

    title = video_info.get("title", "").lower()
    description = video_info.get("description", "").lower()
    owner_lower = owner_name.lower()

    # If owner's name appears in title/description but it's not their channel
    if owner_lower in title or owner_lower in description:
        if owner_lower not in video_info.get("channel", "").lower():
            score += 40  # Big red flag - mentions owner but different channel

    # Common piracy keywords in title
    piracy_keywords = ["highlights", "full match", "leaked", "unofficial", "hd free", "watch free"]
    for keyword in piracy_keywords:
        if keyword in title:
            score += 10  # Each piracy keyword adds suspicion

    return min(score, 95)  # Cap at 95, never claim 100% certainty

def crawl_for_stolen_videos(owner_name, original_filename, watermark_id):
    """
    Main crawler function.
    Searches YouTube for potential stolen copies.
    Returns list of suspicious videos found.
    """
    from database import save_detection  # Import here to avoid circular imports

    queries = build_search_queries(owner_name, original_filename)
    all_suspicious = []
    seen_urls = set()  # Track already-seen URLs to avoid duplicates

    for query in queries:
        print(f"Searching YouTube: {query}")
        results = search_youtube(query, max_results=5)

        for video in results:
            url = video["url"]

            # Skip if we've already seen this URL
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Score how suspicious this video is
            suspicion_score = score_suspicion(video, owner_name)

            # Only flag videos above suspicion threshold
            if suspicion_score >= 50:
                video["suspicion_score"] = suspicion_score
                video["matched_watermark"] = watermark_id
                all_suspicious.append(video)

                # Save to database
                save_detection(
                    video_url=url,
                    detection_type="stolen",
                    confidence=suspicion_score,
                    matched_watermark_id=watermark_id
                )

    return all_suspicious
