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
import time
import random

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

async def analyze_slide_with_gemini(image, api_key: str) -> dict:
    """
    使用 Gemini Vision API 分析單張投影片圖片，提取標題、內文與結構。
    (Async Version)
    """
    try:
        max_retries = 3
        base_delay = 2
        
        # 建立 Client
        client = genai.Client(api_key=api_key)
        
        # 準備內容 (Image processing is CPU bound, run in thread)
        def process_image():
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            return img_byte_arr.getvalue()
            
        img_bytes = await asyncio.to_thread(process_image)
        
        prompt = """
        你是一位專業的簡報設計顧問 (Presentation Consultant)。
        請分析這張簡報投影片圖片，並提取結構化內容。
        
        请以 JSON 格式回傳，包含以下欄位：
        {
            "title": "投影片標題 (若無則自行總結)",
            "content": ["重點1", "重點2", "重點3"],
            "speaker_notes": "演講者備忘錄",
            "layout": "layout_type",
            "main_image_bbox": [ymin, xmin, ymax, xmax],
            "background_color_hex": "#FFFFFF",
            "text_color_hex": "#000000"
        }

        關於 "background_color_hex":
        - 請分析這張投影片的「主要背景顏色」。
        - 如果是淺色底 (如白、米白)，回傳對應 Hex。
        - 如果是深色底 (如黑、深藍)，回傳對應 Hex。
        - 這將用於設定生成的 PPT 背景，讓裁切後的圖片能完美融合，不會有色差邊框。
        
        關於 "text_color_hex":
        - 請根據背景色，建議最易讀的文字顏色 (通常是黑色或白色)。

        關於 "main_image_bbox" (重要的裁切功能!!!):
        - 請精確偵測畫面中「主要圖片/圖表/架構圖」的邊界框 (Bounding Box)。
        - 座標範圍請使用 0-1000 的整數 (normalized coordinate)。格式為 [ymin, xmin, ymax, xmax]。
        - **非常重要**：請盡量「排除」標題文字、頁碼、與右側的 Bullet Points 文字。我只需要圖片/圖表本身。
        - 如果整頁都是文字而沒有明顯的圖片，請回傳 null 或 []。
        - 如果整頁都是圖 (如全版照片)，請回傳 [0, 0, 1000, 1000]。
        
        關於 "layout" 欄位，請從以下選擇最適合的一個：
        - "split_left_image": 圖像包含重要細節 (如複雜圖表、架構圖)，需保留左側大圖。
        - "full_width_text": 圖像僅為裝飾 (如插圖) 或文字量大，適合全寬文字排版。
        - "comparison": 內容包含明顯的對比 (如 Before/After)，適合左右並列。
        """

        for attempt in range(max_retries):
            try:
                # Use Async Client
                response = await client.aio.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.2
                    )
                )
                
                raw_text = response.text
                cleaned_json = clean_json_string(raw_text)
                result = json.loads(cleaned_json)
                
                if isinstance(result, list):
                    if len(result) > 0:
                        result = result[0]
                    else:
                        result = {}
                
                # Default Fallbacks for new fields
                if "background_color_hex" not in result: result["background_color_hex"] = "#FFFFFF"
                if "text_color_hex" not in result: result["text_color_hex"] = "#000000"
                
                return result

            except Exception as e:
                # ... (Error handling omitted for brevity, logic remains same)
                error_str = str(e)
                logger.warning(f"嘗試 {attempt + 1}/{max_retries} 失敗: {error_str}")
                
                 # Retry on Rate Limit
                if ('429' in error_str or 'RESOURCE_EXHAUSTED' in error_str) and attempt < max_retries - 1:
                    sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                    await asyncio.sleep(sleep_time) # Async sleep!
                    continue

                if attempt == max_retries - 1:
                    logger.error(f"Gemini 分析最終失敗: {error_str}")
                    return {
                        "title": "分析暫時無法使用",
                        "content": [f"錯誤: {error_str}", "請稍後再試或更換 API Key"],
                        "layout": "split_left_image",
                        "speaker_notes": "系統無法讀取此頁面。",
                        "main_image_bbox": None, 
                        "background_color_hex": "#FFFFFF",
                        "text_color_hex": "#000000"
                    }
    except Exception as e:
        logger.error(f"分析函式發生外層錯誤: {e}")
        return {}

def hex_to_rgb(hex_color: str) -> RGBColor:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
    return RGBColor(0, 0, 0) # Fallback


async def remove_text_from_image(image, api_key: str):
    """
    使用 Gemini 圖像編輯功能移除圖片上的文字。
    回傳處理後的 PIL Image 物件，若失敗則回傳原圖。
    """
    try:
        from PIL import Image
        
        client = genai.Client(api_key=api_key)
        
        # 準備圖片資料
        def process_image():
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=95)
            return img_byte_arr.getvalue()
        
        img_bytes = await asyncio.to_thread(process_image)
        
        # 使用 Gemini 圖像編輯提示 (使用英文以獲得更好的效果)
        prompt = """
        You are an expert image editor. Your task is to COMPLETELY REMOVE ALL TEXT from this image.

        **CRITICAL INSTRUCTIONS:**
        1. Remove EVERY piece of visible text, including:
           - Titles and headings
           - Bullet points and descriptions
           - Numbers, dates, percentages
           - Watermarks and labels
           - Chinese/Japanese/Korean characters
           - Any alphanumeric characters
        
        2. For each text region you remove:
           - Fill the area with the surrounding background color/texture
           - Use content-aware fill/inpainting to make it seamless
           - Ensure no ghosting or artifacts remain
        
        3. PRESERVE everything that is NOT text:
           - Diagrams, charts, and graphs (only remove text labels)
           - Icons and shapes
           - Images and photos
           - Lines and arrows
        
        4. The output image MUST:
           - Have the EXACT same dimensions as the input
           - Contain ZERO readable text
           - Look natural and clean
        
        DO NOT add any new elements. Only REMOVE text.
        Output the cleaned image directly.
        """
        
        logger.info("嘗試使用 Gemini 移除圖片文字...")
        
        try:
            # 使用支援圖像生成的模型
            response = await client.aio.models.generate_content(
                model='gemini-3-pro-image-preview',  # Nano Banana Pro - 最先進的圖像編輯模型
                contents=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')
                ],
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE', 'TEXT'],  # 要求回傳圖像
                    temperature=0.1
                )
            )
            
            # 檢查回應中是否有圖像
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    # 解碼回傳的圖像
                    edited_bytes = part.inline_data.data
                    edited_image = Image.open(io.BytesIO(edited_bytes))
                    logger.info("✅ 圖片文字移除成功！")
                    return edited_image
            
            # 沒有找到圖像，回傳原圖
            logger.warning("Gemini 未回傳圖像，使用原圖")
            return image
            
        except Exception as e:
            error_str = str(e)
            # 如果模型不支援圖像輸出，嘗試備用方案
            if 'response_modalities' in error_str or 'IMAGE' in error_str:
                logger.warning(f"Gemini 圖像編輯不可用: {error_str}，使用原圖")
            else:
                logger.error(f"Gemini 圖像編輯錯誤: {error_str}")
            return image
            
    except Exception as e:
        logger.error(f"圖像處理外層錯誤: {e}")
        return image


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
        
        # 背景顏色 (Adaptive)
        bg_hex = slide_data.get("background_color_hex", "#18181b") # Default dark if missing
        text_hex = slide_data.get("text_color_hex", "#ffffff")
        
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = hex_to_rgb(bg_hex)
        
        text_rgb = hex_to_rgb(text_hex)
        
        # 2. 處理圖片 (如果有的話)
        layout_type = slide_data.get('layout', 'split_left_image')
        
        # ... (Image Processing Logic continues...)

        img_source = None
        img_byte_arr = None # Initialize outside conditional
        if i < len(images):
            original_img = images[i]
            
            # --- Smart Crop Logic ---
            bbox = slide_data.get('main_image_bbox')
            if bbox and isinstance(bbox, list) and len(bbox) == 4:
                try:
                    # Bbox format: [ymin, xmin, ymax, xmax] (0-1000)
                    ymin, xmin, ymax, xmax = bbox
                    # Validation
                    if 0 <= xmin < xmax <= 1000 and 0 <= ymin < ymax <= 1000:
                        w, h = original_img.size
                        left = int(xmin / 1000 * w)
                        top = int(ymin / 1000 * h)
                        right = int(xmax / 1000 * w)
                        bottom = int(ymax / 1000 * h)
                        
                        logger.info(f"Slide {i+1}: Cropping image to ({left}, {top}, {right}, {bottom})")
                        img_source = original_img.crop((left, top, right, bottom))
                    else:
                         img_source = original_img # Invalid bbox
                except Exception as e:
                    logger.error(f"Crop failed: {e}")
                    img_source = original_img
            else:
                img_source = original_img # No bbox found
            
            if img_source: # Only process if an image source is determined
                img_byte_arr = io.BytesIO()
                img_source.save(img_byte_arr, format='JPEG', quality=95)
                img_byte_arr.seek(0)
            
        
        # 版型分流
        if layout_type == 'full_width_text':
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
                title_p.font.color.rgb = text_rgb # Dynamic Color
                title_p.alignment = 2 # CENTER
                
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
                    p.font.color.rgb = text_rgb # Dynamic Color
                    p.space_after = Pt(20)
                    p.level = 0
            
            # 3. 圖片 (縮小放在右下角裝飾，或是背景浮水印? 這裡先放右下小圖)
            if img_byte_arr: # Use the potentially cropped image if available
                slide.shapes.add_picture(img_byte_arr, Inches(10.5), Inches(5.5), width=Inches(2.5))
                
        else:
            # --- 預設：左圖右文 (split_left_image) ---
            
            # 左側圖片 (Fit into Left Half to prevent overlap)
            # 左側圖片 (Fit into Left Half to prevent overlap)
            if img_source and img_byte_arr:
                # Layout Config
                left_box_w = Inches(6.5) # Approx 50% of 13.33 inches
                left_box_h = prs.slide_height
                
                # Get Aspect Ratio from SOURCE (Cropped or Original)
                img_w, img_h = img_source.size
                if img_h == 0: img_h = 1 # Safety
                aspect = img_w / img_h
                
                # Calculate Box Aspect Ratio
                box_aspect = left_box_w / left_box_h
                
                if aspect > box_aspect:
                    # Wider -> Fit Width, Center Vertically
                    pic = slide.shapes.add_picture(img_byte_arr, Inches(0), Inches(0), width=left_box_w)
                    top_offset = int((left_box_h - pic.height) / 2)
                    pic.top = top_offset
                else:
                    # Taller -> Fit Height, Center Horizontally (in left box)
                    pic = slide.shapes.add_picture(img_byte_arr, Inches(0), Inches(0), height=left_box_h)
                    left_offset = int((left_box_w - pic.width) / 2)
                    pic.left = left_offset
            
            # 右側文字
            text_left = Inches(7.0) # Move slightly right for padding
            text_width = Inches(5.8)
            
            if slide_data.get("title"):
                title_box = slide.shapes.add_textbox(text_left, Inches(0.5), text_width, Inches(1.5))
                title_tf = title_box.text_frame
                title_tf.word_wrap = True
                title_p = title_tf.paragraphs[0]
                title_p.text = slide_data["title"]
                title_p.font.size = Pt(28)
                title_p.font.bold = True
                title_p.font.color.rgb = text_rgb # Dynamic Color
            
            content_items = slide_data.get("content", [])
            if content_items:
                content_box = slide.shapes.add_textbox(text_left, Inches(2.2), text_width, Inches(4.5))
                content_tf = content_box.text_frame
                content_tf.word_wrap = True
                
                for item in content_items:
                    p = content_tf.add_paragraph()
                    p.text = str(item)
                    p.font.size = Pt(16)
                    p.font.color.rgb = text_rgb # Dynamic Color
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

import asyncio

# ... (Previous imports should be preserved, but I need to add asyncio at top ideally, but I can add here or assume added).
# Actually better to add import at top. But for this tool I'll focus on the function body.

async def process_pdf_to_slides(pdf_bytes: bytes, api_key: str, filename: str, selected_indices: Optional[List[int]] = None) -> str:
    """
    主要流程：PDF -> 圖片 -> Gemini 分析 -> 文字移除 -> PPTX
    回傳生成的 PPTX 檔案路徑。
    若有 selected_indices，只處理指定頁面 (0-based index)。
    """
    logger.info(f"開始處理 PDF: {filename}")
    
    # 1. PDF 轉圖片 (Blocking operation, run in thread)
    try:
        # Reduce DPI to 150 to save memory and speed up processing (OOM Prevention)
        images = await asyncio.to_thread(convert_from_bytes, pdf_bytes, dpi=150)
        logger.info(f"成功將 PDF 轉換為 {len(images)} 張圖片 (DPI=150)")
        
        # 過濾頁面
        if selected_indices:
            try:
                # 確保 indices 為整數且在範圍內
                valid_indices = [i for i in selected_indices if 0 <= i < len(images)]
                if valid_indices:
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

    # 2. 逐頁分析 + 文字移除
    analyses = []
    cleaned_images = []
    
    for i, img in enumerate(images):
        logger.info(f"正在分析第 {i+1}/{len(images)} 頁...")
        
        # Use native async call (Non-blocking)
        result = await analyze_slide_with_gemini(img, api_key)
        analyses.append(result)
        
        # 3. 移除圖片上的文字 (新功能)
        logger.info(f"正在移除第 {i+1}/{len(images)} 頁的文字...")
        cleaned_img = await remove_text_from_image(img, api_key)
        cleaned_images.append(cleaned_img)

        # Throttling to avoid Rate Limit (Free Tier ~15 RPM, 加上文字移除共2次呼叫)
        if i < len(images) - 1:
            await asyncio.sleep(3)  # 增加間隔以適應雙倍 API 呼叫

    # 4. 生成 PPTX
    output_dir = "temp_slides"
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{base_name}_converted.pptx")
    
    # 傳入 cleaned_images (已移除文字的圖片) 進行圖文整合排版
    await asyncio.to_thread(create_pptx_from_analysis, analyses, cleaned_images, output_path)
    
    return output_path

