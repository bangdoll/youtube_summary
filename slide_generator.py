import os
import io
import asyncio
import json
import logging
from typing import List, Optional
from PIL import Image
from pdf2image import convert_from_bytes, pdfinfo_from_bytes
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
                    model='gemini-2.0-flash-exp',
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
                        "background_color_hex": "#FFFFFF",
                        "text_color_hex": "#000000"
                    }
    except Exception as e:
        logger.error(f"分析函式發生外層錯誤: {e}")
        return {
             "title": "分析發生錯誤",
             "content": ["無法分析此頁面"],
             "layout": "split_left_image"
        }

def hex_to_rgb(hex_color: str) -> RGBColor:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
    return RGBColor(0, 0, 0) # Fallback


async def remove_text_from_image(image, api_key: str, remove_icon: bool = False):
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
        
        # 使用 Gemini 圖像編輯提示
        base_prompt = "Remove all text from this image and fill the background seamlessly. Do not change anything else."
        
        if remove_icon:
            base_prompt += " ALSO remove the 'NotebookLM' logo, icon, and any footer/page numbers at the bottom."

        prompt = base_prompt
        
        # logger.info("嘗試使用 Gemini 移除圖片文字...") 
        # (Reduce log noise)
        
        try:
            # 使用支援圖像生成的模型
            response = await client.aio.models.generate_content(
                model='gemini-3-pro-image-preview',
                contents=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')
                ],
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE', 'TEXT'],
                    temperature=0.1
                )
            )
            
            # 檢查回應中是否有圖像
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    # 解碼回傳的圖像
                    edited_bytes = part.inline_data.data
                    edited_image = Image.open(io.BytesIO(edited_bytes))
                    # logger.info("✅ 圖片文字移除成功！")
                    return edited_image
            
            return image
            
        except Exception as e:
            # logger.warning(f"Gemini 圖像編輯不可用或失敗: {e}，使用原圖")
            return image
            
    except Exception as e:
        logger.error(f"圖像處理外層錯誤: {e}")
        return image


def crop_visual_element(image, bbox: list, slide_width: int = 1000, slide_height: int = 1000):
    try:
        if not bbox or len(bbox) != 4:
            return None
        ymin, xmin, ymax, xmax = bbox
        img_width, img_height = image.size
        left = int(xmin / slide_width * img_width)
        top = int(ymin / slide_height * img_height)
        right = int(xmax / slide_width * img_width)
        bottom = int(ymax / slide_height * img_height)
        left = max(0, min(left, img_width - 1))
        top = max(0, min(top, img_height - 1))
        right = max(left + 1, min(right, img_width))
        bottom = max(top + 1, min(bottom, img_height))
        return image.crop((left, top, right, bottom))
    except Exception:
        return None


def create_pptx_from_analysis(analyses: List[dict], images: List, output_path: str):
    """
    根據分析結果與原始圖片生成 PPTX 檔案 (Split Layout: 左圖右文)。
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    for i, slide_data in enumerate(analyses):
        try:
            # 建立空白投影片
            slide_layout = prs.slide_layouts[6] # 6 = Blank
            slide = prs.slides.add_slide(slide_layout)
            
            # 背景顏色
            bg_hex = slide_data.get("background_color_hex", "#18181b")
            text_hex = slide_data.get("text_color_hex", "#ffffff")
            
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = hex_to_rgb(bg_hex)
            text_rgb = hex_to_rgb(text_hex)
            
            # 版型
            layout_type = slide_data.get('layout', 'split_left_image')
            
            # 圖片處理
            img_byte_arr = None
            if i < len(images):
                original_img = images[i]
                if original_img:
                    try:
                        # 簡單處理：直接使用傳入的圖片 (已裁切或去字)
                        # 並檢查 bbox 做額外裁切 (視情況)
                        bbox = slide_data.get('main_image_bbox')
                        img_source = original_img
                        if bbox and isinstance(bbox, list) and len(bbox) == 4:
                            # 嘗試裁切
                            cropped = crop_visual_element(original_img, bbox)
                            if cropped: img_source = cropped

                        buf = io.BytesIO()
                        img_source.save(buf, format='JPEG', quality=90)
                        buf.seek(0)
                        img_byte_arr = buf
                    except Exception as e:
                        logger.error(f"Slide {i}: Image processing failed: {e}")

            # --- Layout Implementation ---
            if layout_type == 'full_width_text':
                 if slide_data.get("title"):
                    title_box = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(11.3), Inches(1.5))
                    title_tf = title_box.text_frame
                    title_tf.word_wrap = True
                    title_p = title_tf.paragraphs[0]
                    title_p.text = slide_data["title"]
                    title_p.font.size = Pt(36)
                    title_p.font.bold = True
                    title_p.font.color.rgb = text_rgb
                    title_p.alignment = PP_ALIGN.CENTER
                
                 content_items = slide_data.get("content", [])
                 if content_items:
                    content_box = slide.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.3), Inches(4.5))
                    content_tf = content_box.text_frame
                    content_tf.word_wrap = True
                    for item in content_items:
                        p = content_tf.add_paragraph()
                        p.text = str(item)
                        p.font.size = Pt(20)
                        p.font.color.rgb = text_rgb
                        p.space_after = Pt(20)
            else:
                # Split Layout (Default)
                if img_byte_arr:
                    # Left Image
                    try:
                        pic = slide.shapes.add_picture(img_byte_arr, Inches(0), Inches(0), height=prs.slide_height)
                        # Center in left half (Inches(6.6)) if needed, but full height is good for split
                        # Crop if too wide
                        if pic.width > Inches(7):
                             crop = (pic.width - Inches(7)) / 2
                             pic.crop_left = crop / pic.width
                             pic.crop_right = crop / pic.width
                             pic.left = 0
                    except Exception as e:
                        logger.error(f"Slide {i}: Add picture failed: {e}")

                # Right Text
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
            
            # Speaker Notes
            if slide_data.get("speaker_notes"):
                slide.notes_slide.notes_text_frame.text = slide_data["speaker_notes"]

        except Exception as e:
            logger.error(f"Slide {i} generation failed: {e}")
            continue

    prs.save(output_path)
    logger.info(f"簡報已儲存至: {output_path}")

def generate_preview_images(pdf_bytes: bytes, output_dir: str) -> List[str]:
    try:
        # Reduce memory usage: dpi=100, thread_count=1
        images = convert_from_bytes(pdf_bytes, dpi=100, thread_count=1)
        logger.info(f"預覽生成: 轉換了 {len(images)} 張圖片")
        image_paths = []
        for i, img in enumerate(images):
            filename = f"preview_{secrets.token_hex(4)}_{i}.jpg"
            filepath = os.path.join(output_dir, filename)
            # Resize small thumbnail
            img.thumbnail((400, 400)) # Smaller thumbnail for preview grid
            img.save(filepath, "JPEG", quality=80)
            image_paths.append(f"/static/temp/{filename}")
        return image_paths
    except Exception as e:
        logger.error(f"預覽生成失敗 (Memory/Poppler): {e}")
        raise ValueError(f"無法生成預覽: {str(e)}")


from pdf2image import convert_from_path
from pypdf import PdfReader

async def analyze_presentation(pdf_path: str, api_key: str, filename: str, selected_indices: Optional[List[int]] = None, remove_icon: bool = False, progress_callback: Optional[callable] = None) -> tuple:
    """
    主要流程：PDF (File) -> 圖片 -> Gemini 分析 -> 文字移除
    優化 (v2.10.17): pypdf 秒讀頁數 + 首頁優先策略 (Priority First Page) + 強制超時保護。
    """
    logger.info(f"開始處理 PDF: {filename} (Path: {pdf_path})")
    
    # [Optimization] Notify Start Immediately to update UI from "Preparing"
    if progress_callback:
        try:
             await progress_callback(0, 0, message="正在讀取 PDF 檔案結構...")
        except:
             pass

    try:
        # 1. 快速獲取 PDF 資訊 (使用 pypdf) - 強制 10s Timeout
        # Run in thread because pypdf file reading is sync IO
        def get_pdf_count():
            with open(pdf_path, 'rb') as f:
                reader = PdfReader(f)
                return len(reader.pages)
        
        # TIMEOUT PROTECTION for PDF Reading (10s)
        total_pdf_pages = await asyncio.wait_for(
            asyncio.to_thread(get_pdf_count), 
            timeout=10
        )
        logger.info(f"PDF 總頁數: {total_pdf_pages}")
        
    except asyncio.TimeoutError:
        logger.error("PDF 讀取超時 (pypdf)")
        raise ValueError("PDF 檔案讀取超時，請檢查檔案是否損毀或過大")
        
    except Exception as e:
        logger.error(f"無法讀取 PDF 資訊: {e}")
        raise ValueError(f"無法讀取 PDF 結構: {str(e)}")

    # 決定要處理的頁面索引 (0-based)
    target_indices = selected_indices if selected_indices else list(range(total_pdf_pages))
    target_indices = [i for i in target_indices if 0 <= i < total_pdf_pages]
    target_indices.sort()
    
    if not target_indices:
        return [], []

    analyses = []
    cleaned_images = []
    
    # 策略配置
    BATCH_SIZE = 3
    DELAY_BETWEEN_BATCHES = 1
    TIMEOUT_PER_BATCH = 45 # seconds (Image Conversion)
    TIMEOUT_PER_PAGE_ANALYSIS = 60 # seconds (Gemini API)
    
    async def process_single_page(img, page_num, total):
        logger.info(f"處理第 {page_num}/{total} 頁...")
        try:
             # Wrap AI analysis in timeout
             async def run_ai():
                 try:
                     analysis_task = analyze_slide_with_gemini(img, api_key)
                     text_removal_task = remove_text_from_image(img, api_key, remove_icon=remove_icon)
                     return await asyncio.gather(analysis_task, text_removal_task)
                 except Exception as e:
                     # Log inner exception
                     logger.error(f"AI Task Inner Exception: {e}")
                     raise e
             
             return await asyncio.wait_for(run_ai(), timeout=TIMEOUT_PER_PAGE_ANALYSIS)
             
        except asyncio.TimeoutError:
             logger.error(f"Page {page_num} AI Analysis Timeout")
             return ({
                 "title": "分析超時", 
                 "content": ["AI 回應過慢，請手動編輯"], 
                 "layout": "split_left_image"
             }, img)
        except Exception as e:
             logger.error(f"Page {page_num} critical failure: {e}")
             return ({
                 "title": "分析失敗", 
                 "content": ["請手動編輯此頁面"], 
                 "layout": "split_left_image"
             }, img)

    total_target = len(target_indices)
    
    # Custom Loop for "Priority First Page"
    # We construct batches manually to ensure Batch 1 is SINGLE page (for speed)
    batches = []
    remaining_indices = target_indices.copy()
    
    # Setup First Batch (Priority)
    if remaining_indices:
        # First batch has only 1 page to ensure instant feedback
        batches.append([remaining_indices.pop(0)])
    
    # Setup subsequent batches
    while remaining_indices:
        chunk = remaining_indices[:BATCH_SIZE]
        batches.append(chunk)
        remaining_indices = remaining_indices[BATCH_SIZE:]

    # Execute Batches
    processed_count = 0
    
    for batch_indices in batches:
        current_batch_size = len(batch_indices)
        
        # Notify progress: Converting
        if progress_callback:
            start_p = batch_indices[0] + 1
            end_p = batch_indices[-1] + 1
            msg = f"正在處理第 {start_p}-{end_p} 頁..."
            try:
                await progress_callback(processed_count, total_target, message=msg)
            except Exception as e:
                logger.warning(f"Callback msg failed: {e}")

        # 2. On-Demand Image Conversion (Protected by Timeout)
        batch_images = []
        try:
            # Check for consecutiveness to optimize
            is_consecutive = (len(batch_indices) > 1 and 
                             batch_indices[-1] - batch_indices[0] == len(batch_indices) - 1)
            
            async def run_conversion():
                if is_consecutive:
                    # distinct args for range conversion
                    s = batch_indices[0] + 1
                    e = batch_indices[-1] + 1
                    return await asyncio.to_thread(
                        convert_from_path, pdf_path, dpi=100, 
                        first_page=s, last_page=e, thread_count=1
                    )
                else:
                    imgs = []
                    for idx in batch_indices:
                        p = idx + 1
                        res = await asyncio.to_thread(
                           convert_from_path, pdf_path, dpi=100,
                           first_page=p, last_page=p, thread_count=1
                        )
                        if res: imgs.extend(res)
                    return imgs

            # TIMEOUT WRAPPER
            batch_images = await asyncio.wait_for(run_conversion(), timeout=TIMEOUT_PER_BATCH)
            
        except asyncio.TimeoutError:
            logger.error(f"Batch conversion timed out after {TIMEOUT_PER_BATCH}s")
            batch_images = [Image.new('RGB', (800, 600), color='white') for _ in batch_indices]
        except Exception as e:
            logger.error(f"Batch conversion failed: {e}")
            batch_images = [Image.new('RGB', (800, 600), color='white') for _ in batch_indices]

        # Fail-safe padding
        while len(batch_images) < current_batch_size:
             batch_images.append(Image.new('RGB', (800, 600), color='white'))
        batch_images = batch_images[:current_batch_size]

        # 3. Analyze Batch
        tasks = [
            process_single_page(img, batch_indices[j] + 1, total_pdf_pages)
            for j, img in enumerate(batch_images)
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for k, res in enumerate(batch_results):
            if isinstance(res, Exception):
                logger.error(f"Batch task failed: {res}")
                analyses.append({"title": "錯誤", "content": ["系統發生預期外錯誤"], "layout": "split_left_image"})
                cleaned_images.append(batch_images[k])
            else:
                analyses.append(res[0])
                cleaned_images.append(res[1])
        
        processed_count += current_batch_size
        
        # Report Result Progress
        if progress_callback:
            try:
                await progress_callback(processed_count, total_target)
            except:
                pass

        # Cleanup
        del batch_images
        
        if processed_count < total_target:
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    return analyses, cleaned_images


async def process_pdf_to_slides(pdf_content, api_key: str, filename: str, selected_indices: List[int] = None):
    # Legacy wrapper
    analyses, cleaned_images = await analyze_presentation(pdf_content, api_key, filename, selected_indices)
    output_dir = "temp_slides"
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{base_name}_converted.pptx")
    await asyncio.to_thread(create_pptx_from_analysis, analyses, cleaned_images, output_path)
    return output_path

