import json
import os
import google.generativeai as genai
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

# ============ 設定區 ============
API_KEY = os.environ.get("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CHANNEL_ID = "UC0lbAQVpenvfA2QqzsRtL_g"
MAX_VIDEOS = 5
OUTPUT_FILE = "data/videos.json"
# ================================

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def get_latest_videos(channel_id, max_results=5):
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
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
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

def generate_summary(title, transcript):
    if not transcript:
        return "（無字幕，無法生成摘要）", []
    prompt = f"""
你是一位專業的財經投資分析師，請根據以下影片標題和逐字稿內容：

影片標題：{title}
逐字稿：{transcript[:4000]}

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
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        return data["summary"], data["cards"]
    except Exception as e:
        print(f"  ⚠️ AI 摘要失敗: {e}")
        return "（摘要生成失敗）", []

def main():
    os.makedirs("data", exist_ok=True)
    print("📡 抓取最新影片...")
    videos = get_latest_videos(CHANNEL_ID, MAX_VIDEOS)
    results = []
    for v in videos:
        print(f"🎬 處理：{v['title']}")
        transcript = get_transcript(v["video_id"])
        summary, cards = generate_summary(v["title"], transcript)
        print(f"  ✅ 摘要完成")
        results.append({
            **v,
            "transcript": transcript,
            "summary": summary,
            "cards": cards
        })
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 全部完成！資料存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
