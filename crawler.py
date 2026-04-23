import os
from googleapiclient.discovery import build
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def search_youtube(query, max_results=10):
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results,
            order="date"
        )
        response = request.execute()
        videos = []
        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]
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

def score_suspicion(video_info, owner_name):
    score = 30
    title = video_info.get("title", "").lower()
    description = video_info.get("description", "").lower()
    owner_lower = owner_name.lower()

    if owner_lower in title or owner_lower in description:
        if owner_lower not in video_info.get("channel", "").lower():
            score += 40

    piracy_keywords = ["highlights", "full match", "leaked", "unofficial", "hd free", "watch free"]
    for kw in piracy_keywords:
        if kw in title:
            score += 10

    return min(score, 95)

def crawl_for_stolen_videos(user_id, owner_name, original_filename, watermark_id):
    from database import save_detection

    clean_name = os.path.splitext(original_filename)[0].replace("_", " ").replace("-", " ")
    queries = [
        f"{owner_name} sports clip",
        f"{clean_name} sports highlights",
        f"{owner_name} {clean_name}"
    ]

    all_suspicious = []
    seen_urls = set()

    for query in queries:
        results = search_youtube(query, max_results=5)
        for video in results:
            url = video["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            score = score_suspicion(video, owner_name)
            if score >= 50:
                video["suspicion_score"] = score
                all_suspicious.append(video)
                save_detection(user_id, url, "stolen", score, watermark_id)

    return all_suspicious
