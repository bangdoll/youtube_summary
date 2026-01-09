import os
import io
import json
import logging
from typing import List, Optional
from pdf2image import convert_from_bytes
from pptx import Presentation
from pptx.util import Inches, Pt
from google import genai
from google.genai import types

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',  # 使用快速視覺模型
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')
            ],
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        logger.error(f"Gemini 分析失敗: {e}")
        # 回傳預設空結構以免整份失敗
        return {
            "title": "分析失敗",
            "content": ["無法讀取此頁面內容"],
            "layout": "bullet_points",
            "speaker_notes": ""
        }

def create_pptx_from_analysis(analyses: List[dict], output_path: str):
    """
    根據分析結果生成 PPTX 檔案。
    """
    prs = Presentation()
    
    # 定義母片樣式 (簡單深色主題)
    # 這裡使用預設樣式，實務上可以載入自定義 template.pptx
    
    for slide_data in analyses:
        # 選擇版型 (1 = Title and Content)
        slide_layout = prs.slide_layouts[1] 
        slide = prs.slides.add_slide(slide_layout)
        
        # 設定標題
        title = slide.shapes.title
        if title and slide_data.get("title"):
            title.text = slide_data["title"]
            
        # 設定內容
        body_shape = slide.placeholders[1]
        tf = body_shape.text_frame
        
        content_items = slide_data.get("content", [])
        if content_items:
            tf.text = content_items[0] # 第一點
            
            for item in content_items[1:]:
                p = tf.add_paragraph()
                p.text = item
                p.level = 0
                
        # 設定備忘錄
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
    
    create_pptx_from_analysis(analyses, output_path)
    
    return output_path
