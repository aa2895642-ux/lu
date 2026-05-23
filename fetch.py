import json
import os
import time
import subprocess
import google.generativeai as genai
from googleapiclient.discovery import build

# ============ 設定區 ============
API_KEY = os.environ.get("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OUTPUT_FILE = "data/videos.json"

CHANNELS = [
    {"id": "UC0lbAQVpenvfA2QqzsRtL_g", "name": "游庭皓的財經皓角"},
    {"id": "UCFQsi7WaF5X41tcuOryDk8w", "name": "视野环球财经"},
    {"id": "UC2I5em6UyBpQiO-8ZW0nV3w", "name": "阳光财经"},
    {"id": "UCFhJ8ZFg9W4kLwFTBBNIjOw", "name": "NaNa说美股"},
    {"id": "UCGpj3DO_5_TUDCNUgS9mjiQ", "name": "美投侃新闻"},
]
MAX_VIDEOS_PER_CHANNEL = 1
# ================================

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def get_latest_videos(channel_id, channel_name, max_results=1):
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
            "channel_id": channel_id,
            "channel_name": channel_name,
        })
    return videos

def download_video(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    output = f"/tmp/{video_id}.mp4"
    subprocess.run([
        "yt-dlp", "-f", "worst[ext=mp4]",
        "-o", output, url
    ], check=True)
    return output

def analyze_with_gemini(title, channel_name, video_path):
    print(f"  📤 上傳影片給 Gemini...")
    video_file = genai.upload_file(path=video_path, mime_type="video/mp4")

    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = genai.get_file(video_file.name)

    prompt = f"""
你是一位專業的財經投資分析師，請根據這部影片（頻道：{channel_name}，標題：{title}）：

請提供：
1. 重點摘要（200字以內，繁體中文）
2. 5張精華字卡，每張包含「標題」和「內容」（各一句話）

請用以下 JSON 格式回覆，不要有其他文字：
{{
  "summary": "摘要內容",
  "cards": [
    {{"title": "字卡標題", "content": "字卡內容"}},
    {{"title": "字卡標題", "content": "字卡內容"}},
    {{"title": "字卡標題", "content": "字卡內容"}},
    {{"title": "字卡標題", "content": "字卡內容"}},
    {{"title": "字卡標題", "content": "字卡內容"}}
  ]
}}
"""
    try:
        response = model.generate_content([video_file, prompt])
        text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        genai.delete_file(video_file.name)
        return data["summary"], data["cards"]
    except Exception as e:
        print(f"  ⚠️ Gemini 分析失敗: {e}")
        return "（分析失敗）", []

def main():
    os.makedirs("data", exist_ok=True)
    all_videos = []

    for channel in CHANNELS:
        print(f"\n📡 抓取頻道：{channel['name']}")
        try:
            videos = get_latest_videos(channel["id"], channel["name"], MAX_VIDEOS_PER_CHANNEL)
            for v in videos:
                print(f"  🎬 處理：{v['title']}")
                try:
                    video_path = download_video(v["video_id"])
                    summary, cards = analyze_with_gemini(v["title"], channel["name"], video_path)
                    os.remove(video_path)
                    print(f"  ✅ 完成")
                except Exception as e:
                    print(f"  ❌ 失敗: {e}")
                    summary, cards = "（處理失敗）", []
                all_videos.append({
                    **v,
                    "summary": summary,
                    "cards": cards
                })
        except Exception as e:
            print(f"  ❌ 頻道抓取失敗: {e}")

    # 按日期由新到舊排序
    all_videos.sort(key=lambda x: x["published_at"], reverse=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_videos, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 全部完成！共處理 {len(all_videos)} 部影片")

if __name__ == "__main__":
    main()
