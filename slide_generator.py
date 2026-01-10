import os
import io
import json
import logging
from typing import List, Optional
from pdf2image import convert_from_bytes
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
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
        You are an expert presentation analyst optimizing content for RECONSTRUCTION.
        Your goal is to extract the logical content structure, NOT the physical layout.
        
        Analyze this slide image and return a JSON object with:
        {
            "title": "Concise main title of the slide",
            "content": [
                "Key point 1",
                "Key point 2 (condensed if long)",
                "Key point 3"
            ],
            "speaker_notes": "Detailed speaker notes in Traditional Chinese",
            "background_color_hex": "#FFFFFF",
            "text_color_hex": "#000000",
            "visual_elements": [
                {
                    "type": "photo|diagram|chart",
                    "bbox": [ymin, xmin, ymax, xmax],
                    "description": "Description for alt text"
                }
            ]
        }

        **CRITICAL INSTRUCTIONS:**
        1. **Content Extraction**:
           - Extract the MAIN title.
           - Extract the KEY points as a list of strings in `content`.
           - Ignore page numbers, footers, and decorative text.
           - Keep the language of the original slide (Traditional Chinese if present).

        2. **Visuals**:
           - Identify significant visual elements (charts, photos).
           - Provide `bbox` ONLY for visual elements that need to be preserved/cropped.
           - NO `text_elements` with bboxes are needed. We will reconstruct the text layout programmatically.
        
        3. **Colors**:
           - Detect dominant background and text colors.
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


def crop_visual_element(image, bbox: list, slide_width: int = 1000, slide_height: int = 1000):
    """
    根據正規化邊界框裁切視覺元素。
    
    Args:
        image: PIL Image 物件
        bbox: [ymin, xmin, ymax, xmax] 正規化座標 (0-1000)
        slide_width: 用於正規化的寬度基準
        slide_height: 用於正規化的高度基準
    
    Returns:
        裁切後的 PIL Image，若失敗則回傳 None
    """
    try:
        if not bbox or len(bbox) != 4:
            return None
            
        ymin, xmin, ymax, xmax = bbox
        
        # 轉換正規化座標為實際像素
        img_width, img_height = image.size
        
        left = int(xmin / slide_width * img_width)
        top = int(ymin / slide_height * img_height)
        right = int(xmax / slide_width * img_width)
        bottom = int(ymax / slide_height * img_height)
        
        # 確保座標有效
        left = max(0, min(left, img_width - 1))
        top = max(0, min(top, img_height - 1))
        right = max(left + 1, min(right, img_width))
        bottom = max(top + 1, min(bottom, img_height))
        
        # 裁切
        cropped = image.crop((left, top, right, bottom))
        logger.info(f"裁切視覺元素: ({left}, {top}) -> ({right}, {bottom})")
        return cropped
        
    except Exception as e:
        logger.error(f"裁切視覺元素失敗: {e}")
        return None


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
            
            # --- v2.8.0: 禁用 OCR 精確定位，改用乾淨分離版面 ---
            # text_elements OCR 邊界框不可靠，文字會散落各處
            # 強制使用傳統 Split Layout (左圖右文)
            USE_OCR_POSITIONING = False  # 禁用 OCR 定位
            
            text_elements = slide_data.get("text_elements", [])
            
            if USE_OCR_POSITIONING and text_elements and len(text_elements) > 0:
                # [已禁用] 使用 OCR 偵測到的精確位置
                logger.info(f"Slide {i+1}: Using {len(text_elements)} precise text elements (DISABLED)")
                pass  # 此區塊目前禁用
            else:
                # --- 強制使用：乾淨分離版面 (Split Layout) ---
                # --- 備用：使用傳統標題+內容方式 ---
                text_left = Inches(7.0)
                text_width = Inches(5.8)
                
                if slide_data.get("title"):
                    title_box = slide.shapes.add_textbox(text_left, Inches(0.5), text_width, Inches(1.5))
                    title_tf = title_box.text_frame
                    title_tf.word_wrap = True
                    title_p = title_tf.paragraphs[0]
                    title_p.text = slide_data["title"]
                    title_p.font.size = Pt(28)
                    title_p.font.bold = True
                    title_p.font.color.rgb = text_rgb
                
                content_items = slide_data.get("content", [])
                if content_items:
                    content_box = slide.shapes.add_textbox(text_left, Inches(2.2), text_width, Inches(4.5))
                    content_tf = content_box.text_frame
                    content_tf.word_wrap = True
                    
                    for item in content_items:
                        p = content_tf.add_paragraph()
                        p.text = str(item)
                        p.font.size = Pt(16)
                        p.font.color.rgb = text_rgb
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

async def analyze_presentation(pdf_bytes: bytes, api_key: str, filename: str, selected_indices: Optional[List[int]] = None) -> tuple:
    """
    主要流程：PDF -> 圖片 -> Gemini 分析 -> 文字移除
    回傳 (analyses, cleaned_images)。
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

    # 2. 逐頁分析 + 文字移除 (並行處理以加速)
    analyses = []
    cleaned_images = []
    
    # 每批處理的頁數 (避免 Rate Limit)
    BATCH_SIZE = 3
    DELAY_BETWEEN_BATCHES = 2  # 批次之間的延遲秒數
    
    async def process_single_page(img, page_num, total):
        """並行處理單頁：分析 + 文字移除同時進行"""
        logger.info(f"正在處理第 {page_num}/{total} 頁 (並行分析+文字移除)...")
        
        # 同時執行分析和文字移除
        analysis_task = analyze_slide_with_gemini(img, api_key)
        text_removal_task = remove_text_from_image(img, api_key)
        
        # 等待兩者完成
        result, cleaned_img = await asyncio.gather(analysis_task, text_removal_task)
        
        return result, cleaned_img
    
    # 分批處理以控制 API 負載
    for batch_start in range(0, len(images), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(images))
        batch = images[batch_start:batch_end]
        
        logger.info(f"處理批次 {batch_start//BATCH_SIZE + 1}: 頁 {batch_start+1}-{batch_end}")
        
        # 並行處理批次內的所有頁面
        tasks = [
            process_single_page(img, batch_start + i + 1, len(images))
            for i, img in enumerate(batch)
        ]
        
        batch_results = await asyncio.gather(*tasks)
        
        # 收集結果
        for result, cleaned_img in batch_results:
            analyses.append(result)
            cleaned_images.append(cleaned_img)
        
        # 批次間延遲 (避免 Rate Limit)
        if batch_end < len(images):
            logger.info(f"等待 {DELAY_BETWEEN_BATCHES} 秒後處理下一批...")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    return analyses, cleaned_images


async def process_pdf_to_slides(pdf_content, api_key: str, filename: str, selected_indices: List[int] = None):
    """
    [Legacy Wrapper] 完整流程：PDF -> 分析 -> 去字 -> 生成 PPTX
    保留此函數以相容既有 API。
    """
    
    # 1. 分析與去字
    analyses, cleaned_images = await analyze_presentation(pdf_content, api_key, filename, selected_indices)
    
    # 2. 生成 PPTX
    output_dir = "temp_slides"
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{base_name}_converted.pptx")
    
    # 傳入 cleaned_images (已移除文字的圖片) 進行圖文整合排版
    await asyncio.to_thread(create_pptx_from_analysis, analyses, cleaned_images, output_path)
    
    return output_path

