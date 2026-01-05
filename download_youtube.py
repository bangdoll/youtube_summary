#!/usr/bin/env python3
import argparse
from pytube import YouTube
import pytube.request
import urllib.request

def custom_get(url, **kwargs):
    # 從 kwargs 提取 timeout，如果存在的話
    timeout = kwargs.get("timeout", None)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
        print("Response status:", response.status)
        data = response.read()
        if response.info().get("Content-Encoding") == "gzip":
            import gzip
            data = gzip.decompress(data)
        return data.decode("utf-8")
    except Exception as e:
        print(f"URL Open error: {e}")
        raise

pytube.request.get = custom_get

def download_video(url, output_path="."):
    try:
        yt = YouTube(url)
        # 篩選出 progressive (影音合併)、mp4 格式的影片流，並依解析度由高到低排序後取第一個
        stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
        if not stream:
            print("找不到符合條件的 mp4 影片流。")
            return
        print(f"開始下載：{yt.title}")
        output_file = stream.download(output_path=output_path)
        print(f"下載完成，檔案儲存為：{output_file}")
    except Exception as e:
        print(f"下載過程中發生錯誤：{e}")

def main():
    parser = argparse.ArgumentParser(description="自動下載 YouTube 影片並輸出為 mp4 檔案")
    parser.add_argument("url", help="YouTube 影片網址")
    parser.add_argument("-o", "--output", default=".", help="下載檔案儲存的目錄，預設為當前目錄")
    args = parser.parse_args()
    download_video(args.url, args.output)

if __name__ == "__main__":
    main()