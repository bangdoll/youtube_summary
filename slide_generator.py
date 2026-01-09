import os
import io
import json
import logging
from typing import List, Optional
from pdf2image import convert_from_bytes
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from google import genai
from google.genai import types

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import re

def clean_json_string(text: str) -> str:
    """清理 Gemini 回傳的 JSON 字串 (移除 Markdown 標記)"""
    # 移除 ```json ... ``` 標記
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    return text.strip()

def analyze_slide_with_gemini(image, api_key: str) -> dict:
    """
    使用 Gemini Vision API 分析單張投影片圖片，提取標題、內文與結構。
    """
    try:
        client = genai.Client(api_key=api_key)
        
        prompt = """
        你是一個專業的簡報分析師。請分析這張投影片圖片，並提取結構化資料。
        請以 JSON 格式回傳，欄位如下：
        {
            "title": "投影片標題 (若無則留空)",
            "content": ["重點1", "重點2", ...],
            "layout": "bullet_points" (或是 "title_only", "image_with_caption"),
            "speaker_notes": "演講者備忘錄建議 (繁體中文)"
        }
        請確保提取的文字準確，若有程式碼請保留格式。
        """
        
        # 將 PIL Image 轉為 Bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()

        # 設定安全性以避免誤判 (例如醫學或歷史圖片被當作暴力/不雅)
        # 注意：Gemini SDK v2 的安全性設定方式可能不同，這裡使用通用寬鬆設定
        # 若是透過 google-genai SDK，通常預設已較寬鬆，若需調整可參考官方文件
        # 這裡主要依賴 Prompt Engineering 與 JSON Mode

        response = client.models.generate_content(
            model='gemini-2.0-flash',  # 使用穩定版以獲得較高配額
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')
            ],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.2 # 降低隨機性以確保 JSON 格式穩定
            )
        )
        
        raw_text = response.text
        cleaned_json = clean_json_string(raw_text)
        result = json.loads(cleaned_json)
        
        # 容錯處理：如果 Gemini 回傳 List，取第一個項目
        if isinstance(result, list):
            if len(result) > 0:
                return result[0]
            else:
                return {} # 空 List 回傳空 Dict
                
        return result
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"Gemini 分析失敗: {error_str}")
        if 'response' in locals() and hasattr(response, 'text'):
             logger.error(f"原始回應: {response.text}")
        
        # 檢查是否是 API 配額錯誤，這類錯誤需要向上傳遞
        if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or 'quota' in error_str.lower():
            raise ValueError(f"API 配額已用盡，請稍後再試或更換 API Key。詳情: {error_str[:200]}")
             
        # 其他錯誤回傳預設空結構以免整份失敗
        return {
            "title": "分析失敗",
            "content": [f"錯誤: {error_str}", "請確認您的圖片內容或 API Key 配額"],
            "layout": "bullet_points",
            "speaker_notes": "系統無法讀取此頁面。"
        }

def create_pptx_from_analysis(analyses: List[dict], images: List, output_path: str):
    """
    根據分析結果與原始圖片生成 PPTX 檔案 (Split Layout: 左圖右文)。
    """
    prs = Presentation()
    
    # 設定 16:9 寬螢幕
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    for i, slide_data in enumerate(analyses):
        # 建立空白投影片
        slide_layout = prs.slide_layouts[6] # 6 = Blank
        slide = prs.slides.add_slide(slide_layout)
        
        # 背景：設定為深色
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(17, 17, 17) # 深灰黑背景
        
        # --- 左側：原始 PDF 圖片 (佔 60% 寬度) ---
        if i < len(images):
            # 儲存圖片到記憶體
            img_byte_arr = io.BytesIO()
            images[i].save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            pic_height = prs.slide_height
            # 圖片置左，佔據約 60% 寬度 (約 8 英吋)
            slide.shapes.add_picture(img_byte_arr, Inches(0), Inches(0), height=pic_height)
            
        # --- 右側：AI 分析內容 (佔 40% 寬度) ---
        text_left = Inches(7.8) 
        text_top = Inches(0.5)
        text_width = Inches(5.0)
        
        # 1. 標題文字框
        if slide_data.get("title"):
            title_box = slide.shapes.add_textbox(text_left, text_top, text_width, Inches(1.5))
            title_kf = title_box.text_frame
            title_kf.word_wrap = True
            
            title_p = title_kf.paragraphs[0]
            title_p.text = slide_data["title"]
            title_p.font.size = Pt(28)
            title_p.font.bold = True
        
        # 2. 內容文字框
        content_top = Inches(2.2)
        content_items = slide_data.get("content", [])
        
        if content_items:
            content_box = slide.shapes.add_textbox(text_left, content_top, text_width, Inches(4.5))
            content_tf = content_box.text_frame
            content_tf.word_wrap = True
            
            # 第一點
            p = content_tf.paragraphs[0]
            p.text = str(content_items[0])
            p.font.size = Pt(16)
            p.space_after = Pt(12)
            
            # 後續點
            for item in content_items[1:]:
                p = content_tf.add_paragraph()
                p.text = str(item)
                p.font.size = Pt(16)
                p.space_after = Pt(12)
                p.level = 0
                
        # --- 演講者備忘錄 ---
        if slide_data.get("speaker_notes"):
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = slide_data["speaker_notes"]
            
    prs.save(output_path)
    logger.info(f"簡報已儲存至: {output_path}")

async def process_pdf_to_slides(pdf_bytes: bytes, api_key: str, filename: str) -> str:
    """
    主要流程：PDF -> 圖片 -> Gemini 分析 -> PPTX
    回傳生成的 PPTX 檔案路徑。
    """
    logger.info(f"開始處理 PDF: {filename}")
    
    # 1. PDF 轉圖片
    try:
        images = convert_from_bytes(pdf_bytes)
        logger.info(f"成功將 PDF 轉換為 {len(images)} 張圖片")
    except Exception as e:
        logger.error(f"PDF 轉圖片失敗: {e}")
        raise ValueError("無法讀取 PDF 檔案，請確認格式是否正確 (需安裝 poppler)")

    # 2. 逐頁分析
    analyses = []
    for i, img in enumerate(images):
        logger.info(f"正在分析第 {i+1}/{len(images)} 頁...")
        result = analyze_slide_with_gemini(img, api_key)
        analyses.append(result)

    # 3. 生成 PPTX
    output_dir = "temp_slides"
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{base_name}_converted.pptx")
    
    # 傳入 images 進行圖文整合排版
    create_pptx_from_analysis(analyses, images, output_path)
    
    return output_path
