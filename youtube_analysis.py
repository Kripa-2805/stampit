import os
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

def analyze_youtube_url(url):
    """
    Takes a YouTube URL, fetches video metadata via YouTube Data API,
    and flags suspicious signals that may indicate deepfake/stolen content.
    """
    if not API_KEY:
        return {"error": "YouTube API key missing. Add YOUTUBE_API_KEY to your .env file."}

    # Extract video ID from URL
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Invalid YouTube URL. Please paste a valid YouTube video link."}

    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)

        # Fetch video details
        video_response = youtube.videos().list(
            part="snippet,statistics,status",
            id=video_id
        ).execute()

        if not video_response['items']:
            return {"error": "Video not found or is private."}

        video = video_response['items'][0]
        snippet = video['snippet']
        statistics = video.get('statistics', {})
        status = video.get('status', {})

        # Fetch channel details
        channel_id = snippet['channelId']
        channel_response = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        ).execute()

        channel = channel_response['items'][0] if channel_response['items'] else {}
        channel_snippet = channel.get('snippet', {})
        channel_stats = channel.get('statistics', {})

        # --- SUSPICIOUS SIGNAL ANALYSIS ---
        flags = []
        score = 0  # Higher = more suspicious

        # 1. Channel age — new channels are suspicious
        channel_created = channel_snippet.get('publishedAt', '')
        if channel_created:
            created_date = datetime.fromisoformat(channel_created.replace('Z', '+00:00'))
            days_old = (datetime.now(timezone.utc) - created_date).days
            if days_old < 30:
                flags.append("⚠️ Channel is less than 30 days old")
                score += 30
            elif days_old < 90:
                flags.append("⚠️ Channel is less than 90 days old")
                score += 15

        # 2. No description
        if not snippet.get('description', '').strip():
            flags.append("⚠️ Video has no description")
            score += 10

        # 3. Comments disabled
        if status.get('publicStatsViewable') == False:
            flags.append("⚠️ Public stats hidden")
            score += 10

        # 4. Very low subscriber count on channel
        subscriber_count = int(channel_stats.get('subscriberCount', 0))
        if subscriber_count < 100:
            flags.append(f"⚠️ Channel has very few subscribers ({subscriber_count})")
            score += 25
        elif subscriber_count < 1000:
            flags.append(f"⚠️ Channel has low subscribers ({subscriber_count})")
            score += 10

        # 5. Like/View ratio anomaly (too high = bot boosted)
        view_count = int(statistics.get('viewCount', 0))
        like_count = int(statistics.get('likeCount', 0))
        if view_count > 0:
            like_ratio = (like_count / view_count) * 100
            if like_ratio > 20:
                flags.append(f"⚠️ Unusually high like ratio ({like_ratio:.1f}%) — possible bot activity")
                score += 20

        # 6. Title contains suspicious keywords
        title = snippet.get('title', '').lower()
        suspicious_keywords = ['leaked', 'exclusive', 'rare', 'banned', 'removed', 'original', 'real footage']
        for kw in suspicious_keywords:
            if kw in title:
                flags.append(f"⚠️ Title contains suspicious keyword: '{kw}'")
                score += 15
                break

        # 7. No channel description
        if not channel_snippet.get('description', '').strip():
            flags.append("⚠️ Channel has no description")
            score += 10

        # Determine verdict
        if score >= 50:
            verdict = "HIGH RISK"
            verdict_color = "red"
        elif score >= 25:
            verdict = "SUSPICIOUS"
            verdict_color = "orange"
        else:
            verdict = "LIKELY SAFE"
            verdict_color = "green"

        return {
            "video_id": video_id,
            "title": snippet.get('title', 'Unknown'),
            "channel": snippet.get('channelTitle', 'Unknown'),
            "channel_subscribers": subscriber_count,
            "views": view_count,
            "likes": like_count,
            "published": snippet.get('publishedAt', '')[:10],
            "flags": flags,
            "risk_score": min(score, 100),
            "verdict": verdict,
            "verdict_color": verdict_color,
            "url": url
        }

    except Exception as e:
        return {"error": f"API error: {str(e)}"}


def extract_video_id(url):
    """Extracts video ID from various YouTube URL formats."""
    import re
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
