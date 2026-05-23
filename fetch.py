import json
import os
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

# ============ 設定區 ============
API_KEY = "AIzaSyCXWS5JkmNr7i_Vy1OUSWlwbIY4RxwmKMg"
CHANNEL_ID = "UC0lbAQVpenvfA2QqzsRtL_g"  # 目標頻道
MAX_VIDEOS = 5  # 每次抓幾部影片
OUTPUT_FILE = "data/videos.json"
# ================================

def get_latest_videos(channel_id, max_results=5):
    """取得頻道最新影片清單"""
    youtube = build("youtube", "v3", developerKey=API_KEY)
    
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=max_results,
        order="date",
        type="video"
    )
    response = request.execute()
    
    videos = []
    for item in response["items"]:
        videos.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "published_at": item["snippet"]["publishedAt"],
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
        })
    return videos

def get_transcript(video_id):
    """取得影片字幕（優先中文，其次英文）"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 優先取中文字幕
        try:
            transcript = transcript_list.find_transcript(["zh-TW", "zh-Hans", "zh"])
        except:
            transcript = transcript_list.find_generated_transcript(["zh-TW", "zh", "en"])
        
        entries = transcript.fetch()
        full_text = " ".join([e["text"] for e in entries])
        return full_text
    except Exception as e:
        print(f"  ⚠️ 無法取得字幕 {video_id}: {e}")
        return None

def main():
    os.makedirs("data", exist_ok=True)
    
    print("📡 抓取最新影片...")
    videos = get_latest_videos(CHANNEL_ID, MAX_VIDEOS)
    
    results = []
    for v in videos:
        print(f"🎬 處理：{v['title']}")
        transcript = get_transcript(v["video_id"])
        results.append({
            **v,
            "transcript": transcript,
            "summary": None,  # 下一步由 AI 填入
            "cards": []
        })
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！資料存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
