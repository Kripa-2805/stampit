import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

def hunt_stolen_videos(keyword):
    """
    Searches YouTube for keywords and checks if the 
    videos match the user's stamped fingerprints.
    """
    if not API_KEY:
        return [{"url": "Error", "status": "API Key Missing"}]

    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    # Search for videos matching the keyword (e.g., "Virat Kohli Six")
    request = youtube.search().list(
        q=keyword,
        part="snippet",
        maxResults=5,
        type="video"
    )
    response = request.execute()

    found_stolen = []
    for item in response['items']:
        video_id = item['id']['videoId']
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # SIMULATION: Check if this video's fingerprint matches the owner's
        # In reality: download 10s clip -> run watermark.verify_stamp()
        if random.random() > 0.7: # 30% chance to find a "stolen" copy
            found_stolen.append({"url": url, "title": item['snippet']['title']})
            
    return found_stolen

import random # Required for the simulation above
