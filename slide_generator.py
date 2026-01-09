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
import re
import secrets

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
        你是一位專業的簡報設計顧問 (Presentation Consultant)。
        請分析這張投影片，提取核心洞察並建議最佳的 PPTX 重製版型。
        
        請以對應的繁體中文 JSON 格式回傳：
        {
            "title": "精簡有力的標題 (不超過 20 字)",
            "content": ["關鍵洞察 1", "關鍵數據/論點 2", "行動建議 3"], 
            "layout": "split_left_image", 
            "speaker_notes": "演講者備忘錄 (口語化，解釋圖表或延伸觀點)"
        }
        
        關於 "layout" 欄位，請從以下選擇最適合的一個：
        - "split_left_image": 圖像包含重要細節 (如複雜圖表、架構圖)，需保留左側大圖。
        - "full_width_text": 圖像僅為裝飾 (如插圖) 或文字量大，適合全寬文字排版。
        - "comparison": 內容包含明顯的對比 (如 Before/After)，適合左右並列。
        
        請確保內容不僅是「描述圖片」，而是提取「核心價值」與「商業洞察」。
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
        
        layout_type = slide_data.get("layout", "split_left_image")
        
        # --- Layout Logic ---
        
        if layout_type == "full_width_text":
            # --- 全寬文字版型 ---
            
            # 1. 標題居中/置頂
            if slide_data.get("title"):
                title_box = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(11.3), Inches(1.5))
                title_tf = title_box.text_frame
                title_tf.word_wrap = True
                title_p = title_tf.paragraphs[0]
                title_p.text = slide_data["title"]
                title_p.font.size = Pt(36)
                title_p.font.bold = True
                title_p.alignment = 2 # CENTER (PP_ALIGN.CENTER but using int 2 for simplicity if not imported)
                
            # 2. 內容全寬
            content_items = slide_data.get("content", [])
            if content_items:
                content_box = slide.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.3), Inches(4.5))
                content_tf = content_box.text_frame
                content_tf.word_wrap = True
                
                for item in content_items:
                    p = content_tf.add_paragraph()
                    p.text = str(item)
                    p.font.size = Pt(20) # 較大字體
                    p.space_after = Pt(20)
                    p.level = 0
            
            # 3. 圖片 (縮小放在右下角裝飾，或是背景浮水印? 這裡先放右下小圖)
            if i < len(images):
                img_byte_arr = io.BytesIO()
                images[i].save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                slide.shapes.add_picture(img_byte_arr, Inches(10.5), Inches(5.5), width=Inches(2.5))
                
        else:
            # --- 預設：左圖右文 (split_left_image) ---
            
            # 左側圖片
            if i < len(images):
                img_byte_arr = io.BytesIO()
                images[i].save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                pic_height = prs.slide_height
                slide.shapes.add_picture(img_byte_arr, Inches(0), Inches(0), height=pic_height)
            
            # 右側文字
            text_left = Inches(7.8)
            text_width = Inches(5.0)
            
            if slide_data.get("title"):
                title_box = slide.shapes.add_textbox(text_left, Inches(0.5), text_width, Inches(1.5))
                title_tf = title_box.text_frame
                title_tf.word_wrap = True
                title_p = title_tf.paragraphs[0]
                title_p.text = slide_data["title"]
                title_p.font.size = Pt(28)
                title_p.font.bold = True
            
            content_items = slide_data.get("content", [])
            if content_items:
                content_box = slide.shapes.add_textbox(text_left, Inches(2.2), text_width, Inches(4.5))
                content_tf = content_box.text_frame
                content_tf.word_wrap = True
                
                for item in content_items:
                    p = content_tf.add_paragraph()
                    p.text = str(item)
                    p.font.size = Pt(16)
                    p.space_after = Pt(12)
                    p.level = 0

        # --- 演講者備忘錄 (通用) ---
        if slide_data.get("speaker_notes"):
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = slide_data["speaker_notes"]
            
    prs.save(output_path)
    logger.info(f"簡報已儲存至: {output_path}")

def generate_preview_images(pdf_bytes: bytes, output_dir: str) -> List[str]:
    """
    將 PDF 轉換為圖片並儲存，用於前端預覽。
    回傳圖片的相對路徑列表。
    """
    try:
        images = convert_from_bytes(pdf_bytes)
        logger.info(f"預覽生成: 轉換了 {len(images)} 張圖片")
        
        image_paths = []
        for i, img in enumerate(images):
            # 檔名使用隨機數以避免快取問題，或需定期清理
            filename = f"preview_{secrets.token_hex(4)}_{i}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            # Resize 圖片以加快傳輸 (例如寬度 800)
            img.thumbnail((800, 800))
            img.save(filepath, "JPEG", quality=80)
            
            # 回傳給前端的相對 URL
            image_paths.append(f"/static/temp/{filename}")
            
        return image_paths
    except Exception as e:
        logger.error(f"預覽生成失敗: {e}")
        raise ValueError(f"無法生成預覽: {e}")

async def process_pdf_to_slides(pdf_bytes: bytes, api_key: str, filename: str, selected_indices: Optional[List[int]] = None) -> str:
    """
    主要流程：PDF -> 圖片 -> Gemini 分析 -> PPTX
    回傳生成的 PPTX 檔案路徑。
    若有 selected_indices，只處理指定頁面 (0-based index)。
    """
    logger.info(f"開始處理 PDF: {filename}")
    
    # 1. PDF 轉圖片
    try:
        images = convert_from_bytes(pdf_bytes)
        logger.info(f"成功將 PDF 轉換為 {len(images)} 張圖片")
        
        # 過濾頁面
        if selected_indices:
            try:
                # 確保 indices 為整數且在範圍內
                valid_indices = [i for i in selected_indices if 0 <= i < len(images)]
                if valid_indices:
                    # 按照 user 選擇的順序重新排列 (或是保持原本順序但過濾)
                    # 這裡假設 user 想要保持順序
                    valid_indices.sort()
                    images = [images[i] for i in valid_indices]
                    logger.info(f"篩選後剩餘 {len(images)} 頁 (Indices: {valid_indices})")
                else:
                    logger.warning("提供的 selected_indices 無效，使用全部頁面")
            except Exception as e:
                logger.error(f"頁面篩選失敗: {e}, 使用全部頁面")
                
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
