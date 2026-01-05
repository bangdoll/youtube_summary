from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

video_id = "9J_o779xb5k"

try:
    # Try fetching Traditional Chinese, then Simplified, then English
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['zh-Hant', 'zh-TW', 'zh-Hans', 'zh-CN', 'en'])
    formatter = TextFormatter()
    text_formatted = formatter.format_transcript(transcript)
    with open("transcript_raw.txt", "w", encoding="utf-8") as f:
        f.write(text_formatted)
    print("Transcript saved to transcript_raw.txt")
except Exception as e:
    print(f"Error fetching transcript: {e}")
