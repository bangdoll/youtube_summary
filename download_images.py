import os
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import logging
import json
import time

# 設定日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImageDownloader:
    def __init__(self):
        self.article_url = "https://www.bnext.com.tw/article/82767/ai-50"
        self.save_dir = Path("images/台灣AI公司")
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
    def download_image(self, url, filename):
        """下載單一圖片"""
        try:
            # 處理相對路徑
            if url.startswith('/'):
                url = f"https://www.bnext.com.tw{url}"
            
            logger.info(f"開始下載圖片: {url}")
            response = requests.get(url, headers=self.headers)
            logger.debug(f"回應狀態碼: {response.status_code}")
            logger.debug(f"回應標頭: {json.dumps(dict(response.headers), indent=2)}")
            
            if response.status_code == 200:
                image_path = self.save_dir / filename
                with open(image_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"成功下載圖片: {filename}")
                return True
            else:
                logger.error(f"下載圖片失敗: {url}, 狀態碼: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"下載圖片時發生錯誤: {str(e)}")
            return False
            
    def extract_images(self):
        """從文章中提取圖片"""
        try:
            logger.info(f"開始獲取文章: {self.article_url}")
            response = requests.get(self.article_url, headers=self.headers)
            logger.debug(f"文章回應狀態碼: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                logger.debug(f"網頁標題: {soup.title.string if soup.title else 'No title found'}")
                
                # 保存網頁內容以供調試
                with open("webpage_content.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info("已保存網頁內容供調試")
                
                # 尋找文章中的圖片
                images = soup.find_all(['img', 'meta'])  # 同時搜尋 img 標籤和 meta 標籤
                logger.info(f"找到 {len(images)} 個圖片相關標籤")
                
                for i, img in enumerate(images):
                    # 檢查是否為 meta 標籤且包含 og:image
                    if img.name == 'meta' and img.get('property') == 'og:image':
                        src = img.get('content')
                    else:
                        src = img.get('src')
                        
                    logger.debug(f"圖片 {i+1}: {src}")
                    if src:
                        # 檢查是否為文章相關圖片
                        if 'album/2025-03' in src:
                            filename = f"ai_company_{i+1}.jpg"
                            logger.info(f"找到相關圖片: {src}")
                            time.sleep(1)  # 添加延遲以避免被封鎖
                            self.download_image(src, filename)
                        else:
                            logger.debug(f"跳過不相關的圖片: {src}")
            else:
                logger.error(f"獲取文章失敗: {response.status_code}")
        except Exception as e:
            logger.error(f"提取圖片時發生錯誤: {str(e)}")

if __name__ == "__main__":
    downloader = ImageDownloader()
    downloader.extract_images() 