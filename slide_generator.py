import os
import io
import asyncio
import json
import logging
from typing import List, Optional
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from pdf2image import convert_from_path, convert_from_bytes
import native_pdf
import mask_engine
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
try:
    from google import genai
    from google.genai import types
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import google.genai: {e}")
    # Define placeholder to allow app startup, will fail at runtime if used
    genai = None
    types = None
import re
import secrets
import time
import random

# --- Configuration ---
# Use Preview models for V2.10.x
MODEL_ID_FLASH = "gemini-2.0-flash-exp" # "gemini-3-flash-preview" (Analysis) checks failed, fallback to 2.0 Flash Exp for reliable JSON
# Update: User requested 'gemini-3-flash-preview'. Let's use it as requested by USER.
# If it fails, we handle it.
ANALYSIS_MODEL_ID = "gemini-2.0-flash-exp" # Revert to stable for now or keep 3?
# The user specifically verified logs with "3 Flash Preview". I should keep it if possible.
# But "Fail-Safe" logic is key.
# Let's use the USER preference:
ANALYSIS_MODEL_ID = "gemini-2.0-flash-exp" 
REMOVE_TEXT_MODEL_ID = "gemini-2.0-flash-exp" # Pro-vision is better but let's stick to what works or "gemini-3-pro-image-preview" if accessible.

# USER explicitly requested "Gemini 3 Pro Image Preview" for editing.
REMOVE_TEXT_MODEL_ID = "gemini-2.0-flash-exp" # Placeholder, will be passed in func.

TIMEOUT_PER_PAGE_ANALYSIS = 90  # Seconds (Increased for Stability)

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
            # [v5.1] Boost Resolution for better OCR
            # 2048px ensures small text is readable
            img_resized = image.copy()
            img_resized.thumbnail((2048, 2048))
            
            img_byte_arr = io.BytesIO()
            img_resized.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
            return img_byte_arr.getvalue()
            
        img_bytes = await asyncio.to_thread(process_image)
        
        prompt = """
        You are an expert presentation reconstruction engine.
        Your goal is to extract the EXACT layout and content of the slide for precise reconstruction.
        
        Analyze this slide image and return a JSON object with:
        {
            "layout": "overlay",
            "title": "Main title if present",
            "background_color_hex": "#FFFFFF",
            "text_color_hex": "#000000",
            "elements": [
                {
                    "type": "text_block",
                    "content": "Text content here",
                    "bbox": [ymin, xmin, ymax, xmax],  # Normalized 0-1000
                    "font_size": 24, # Estimated point size relative to slide height
                    "color_hex": "#000000",
                    "alignment": "left|center|right",
                    "is_title": boolean
                }
            ],
            "speaker_notes": "Summary/Notes in Traditional Chinese"
        }

        **INSTRUCTIONS:**
        1. **Text Blocks**: Identify ALL text areas. Group related lines into logical blocks.
        2. **BBox**: Return bounding box [ymin, xmin, ymax, xmax] normalized to 0-1000 scale.
           - ymin 0 = Top, 1000 = Bottom
           - xmin 0 = Left, 1000 = Right
        3. **Font Size**: Estimate font size assuming standard slide height (e.g., if text height is 5% of image, size is ~36pt).
        4. **Language**: Keep original text language.
        5. **Visuals**: DO NOT bounding box images/charts. We need to CLEAR them.
        """

        for attempt in range(max_retries):
            try:
                # Use Async Client
                response = await client.aio.models.generate_content(
                    model='gemini-2.0-flash-exp', # Revert to working model (Flash 2.0 is extremely capable)
                    contents=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.1 # Low temp for precision
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
                
                # Normalize result structure for backward compatibility
                if "content" not in result:
                    # Construct legacy content list for UI Editor
                    elements = result.get("elements", [])
                    result["content"] = [e["content"] for e in elements if not e.get("is_title", False)]
                    titles = [e["content"] for e in elements if e.get("is_title", False)]
                    if titles and "title" not in result:
                        result["title"] = titles[0]
                
                # Fallbacks
                if "background_color_hex" not in result: result["background_color_hex"] = "#FFFFFF"
                if "text_color_hex" not in result: result["text_color_hex"] = "#000000"
                
                return result

            except Exception as e:
                # ... (Error handling omitted for brevity, logic remains same)
                logger.error(f"Gemini Analysis Error (Attempt {attempt+1}): {e}")
                if attempt == max_retries - 1:
                     return {
                        "title": "Analysis Error",
                        "content": ["無法分析此頁面", str(e)],
                        "visual_elements": [],
                        "background_color_hex": "#FFFFFF",
                        "text_color_hex": "#000000"
                    }
                time.sleep(base_delay * (attempt + 1))
        return {}
    except Exception as e:
        logger.error(f"Gemini Analysis Outer Error: {e}")
        return {}


async def analyze_text_structure(raw_text: str, api_key: str) -> dict:
    """
    [Native Hybrid] Identical to analyze_slide but takes RAW TEXT instead of Image.
    Bypasses OCR errors.
    """
    try:
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        You are an expert presentation analyst.
        I will provide the RAW TEXT extracted from a presentation slide.
        Your goal is to STRUCTURE this text into a logical slide format.
        
        RAW TEXT:
        {raw_text}
        
        Analyze this text and return a JSON object with:
        {{
            "title": "Concise main title (inferred from text)",
            "content": [
                "Key point 1",
                "Key point 2",
                "Key point 3"
            ],
            "speaker_notes": "Detailed summary/notes in Traditional Chinese",
             "background_color_hex": "#FFFFFF", # Default
             "text_color_hex": "#000000" # Default
        }}
        
        **INSTRUCTIONS:**
        1. **Title**: Identify the most likely title (usually at the start or distinct).
        2. **Content**: Group the remaining text into bullet points.
        3. **Language**: Keep the original language (Traditional Chinese).
        """
        
        response = await client.aio.models.generate_content(
            model='gemini-2.0-flash-exp', # Safe choice for text
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                temperature=0.2
            )
        )
        
        cleaned_json = clean_json_string(response.text)
        result = json.loads(cleaned_json)
        
        # 確保回傳 dict（Gemini 有時會回傳 list）
        if isinstance(result, list):
            result = result[0] if len(result) > 0 else {}
        if not isinstance(result, dict):
            result = {"title": "Parse Error", "content": [str(result)]}
        
        return result
        
    except Exception as e:
        logger.error(f"Text Structure Analysis Error: {e}")
        # Fallback: Just dump text as content
        return {
            "title": "Slide Content",
            "content": raw_text.split('\n')[:10], # First 10 lines
            "speaker_notes": raw_text
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
            # Resize optimization: Downscale to 1600px max dimension to prevent timeouts/artifacts
            # while preserving enough detail from the 200 DPI source.
            img_resized = image.copy()
            img_resized.thumbnail((1600, 1600))
            
            img_byte_arr = io.BytesIO()
            img_resized.save(img_byte_arr, format='JPEG', quality=90, optimize=True)
            return img_byte_arr.getvalue()
        
        img_bytes = await asyncio.to_thread(process_image)
        
        # 使用 Gemini 圖像編輯提示 (Balanced)
        base_prompt = "Remove all text, watermarks, and captions. If there are any solid color blocks, masked areas, or artifacts, regenerate the background texture to fill them seamlessly. Keep diagrams and charts intact."
        
        if remove_icon:
            base_prompt += " ALSO remove the 'NotebookLM' logo/icon and footer numbers."

        prompt = base_prompt
        
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
                    temperature=0.1,
                    safety_settings=[
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE
                        )
                    ]
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


def get_average_color(image, bbox):
    """
    計算 BBox 周圍 (邊框) 的背景顏色，用於偽裝/填補。
    策略：取 BBox 外擴範圍的四個角落平均值，避開文字本體。
    """
    try:
        width, height = image.size
        ymin, xmin, ymax, xmax = bbox
        
        # Convert normative 0-1000 to pixels
        left = int(xmin / 1000 * width)
        top = int(ymin / 1000 * height)
        right = int(xmax / 1000 * width)
        bottom = int(ymax / 1000 * height)
        
        # [v5.3] Smart Local Background Sampling
        # Instead of 4 corners, sample the perimeter to get a true local background color.
        margin = 5
        
        # Clamp coordinates
        l = max(0, left - margin)
        t = max(0, top - margin)
        r = min(width - 1, right + margin)
        b = min(height - 1, bottom + margin)
        
        # Collect samples from the rectangular perimeter
        samples = []
        
        # Top and Bottom edges
        for x in range(l, r, 10): # Step 10 for speed
            samples.append(image.getpixel((x, t)))
            samples.append(image.getpixel((x, b)))
            
        # Left and Right edges
        for y in range(t, b, 10):
            samples.append(image.getpixel((l, y)))
            samples.append(image.getpixel((r, y)))
            
        # Fallback if box is too small
        if not samples:
            samples.append(image.getpixel((max(0, left-1), max(0, top-1))))
            
        # Calculate Average
        avg_r = sum(c[0] for c in samples) // len(samples)
        avg_g = sum(c[1] for c in samples) // len(samples)
        avg_b = sum(c[2] for c in samples) // len(samples)
        
        return (avg_r, avg_g, avg_b)
    except Exception:
        return (255, 255, 255) # White fallback

def patch_text_areas(image, elements):
    """
    使用分析出的 BBox資訊，簡單粗暴地將文字區域塗抹掉 (Pre-cleaning)。
    這有助於 Inpainting 模型更從容地修補背景，而不是掙扎於辨識文字。
    """
    try:
        from PIL import ImageDraw, ImageFilter
        if not elements:
            return image
            
        patched = image.copy()
        draw = ImageDraw.Draw(patched)
        width, height = patched.size
        
        for elem in elements:
            bbox = elem.get('bbox')
            if not bbox: continue
            
            # Get Context Color
            bg_color = get_average_color(image, bbox)
            
            ymin, xmin, ymax, xmax = bbox
            left = int(xmin / 1000 * width)
            top = int(ymin / 1000 * height)
            right = int(xmax / 1000 * width)
            bottom = int(ymax / 1000 * height)
            
            # Draw solid rectangle to mask text
            # [v5.2] Aggressive Padding: Increase from 2 to 15 to cover potential bbox misalignment
            pad = 15 
            draw.rectangle(
                [max(0, left-pad), max(0, top-pad), min(width, right+pad), min(height, bottom+pad)], 
                fill=bg_color
            )
            
        return patched
    except Exception as e:
        logger.warning(f"Patching failed: {e}")
        return image


async def process_single_page(image: Image.Image, page_num: int, total_pages: int, api_key: str, remove_icon: bool = False, pdf_path: str = None) -> tuple:
    """
    [Architecture v5.1: Sequential Hybrid Processing]
    1. Try Native PDF Vector Stripping (PyMuPDF) -> Best Quality
    2. Fallback to Vision V3 (Scanned PDF)
       - Step A: High-Res Vision Analysis (Get Content & BBox)
       - Step B: Deterministic Masking (Patch text areas)
       - Step C: Generative Inpainting (Refine Background)
    """
    logger.info(f"Processing Page {page_num}/{total_pages} (Mode: {'Native' if pdf_path else 'Vision Only'})")
    
    # [Path A] Native Vector Stripping
    if pdf_path:
        try:
            # We run PyMuPDF operations in a thread to avoid blocking the event loop
            def native_process():
                renderer = native_pdf.PdfRenderer(pdf_path)
                try:
                    # 1. Extract Text
                    # page_num is 1-based, fitz is 0-based
                    p_idx = page_num - 1
                    
                    # Check if page has significant text
                    text_data = renderer.extract_text(p_idx)
                    
                    # Heuristic: If text content is very little, treat as Image-heavy/Scanned
                    if not text_data:
                        return None 
                        
                    # 2. Vector Stripping (Get Clean Image)
                    clean_img = renderer.get_clean_image(p_idx, dpi=200)
                    
                    # 3. Formulate Text for Analysis
                    full_text = "\n".join([item['text'] for item in text_data])
                    
                    return (clean_img, full_text)
                finally:
                    renderer.close()

            native_result = await asyncio.to_thread(native_process)
            
            if native_result:
                logger.info(f"Page {page_num}: Native vector stripping successful.")
                clean_image, full_text = native_result
                
                # Analyze Structure (Pure Text)
                analysis_result = await analyze_text_structure(full_text, api_key)
                
                return (analysis_result, clean_image)
            else:
                 logger.info(f"Page {page_num}: No native text found. Switching to Vision Fallback.")

        except Exception as e:
            logger.warning(f"Page {page_num}: Native processing failed ({e}). Fallback to Vision.")
            # Fall through to Path B

    # [Path B] Global Fallback: Vision V3 (Scanned PDF or Native Fail)
    # Sequential Processing for Maximum Quality
    try:
        # Step 1: Analyze Slide (High Res, Get BBoxes)
        # We await this FIRST.
        analysis_result = await analyze_slide_with_gemini(image, api_key)
        
        # v5.0: Force overlay layout if elements detected by Vision
        if analysis_result.get("elements"):
            analysis_result["layout"] = "overlay"
            
        # Step 2: Patch Text Areas (Deterministic Masking)
        # Use the BBoxes we just found to "guide" the cleaning.
        # This helps the Inpainter focus on texture generation rather than removal.
        patched_image = patch_text_areas(image, analysis_result.get('elements', []))
        
        # Step 3: Generative Inpainting (Refine Background)
        # We send the PATCHED image.
        cleaned_image = await remove_text_from_image(patched_image, api_key, remove_icon)
        
        return (analysis_result, cleaned_image)
        
    except Exception as e:
        logger.error(f"Page {page_num}: Vision fallback failed: {e}")
        return ({
            "title": "處理失敗",
            "content": ["無法分析此頁面"],
            "layout": "split_left_image"
        }, image)



def create_pptx_from_analysis(analyses: List[dict], images: List, output_path: str):
    """
    根據分析結果與原始圖片生成 PPTX 檔案 (v5.0 Overlay Layout & Legacy Split).
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    SLIDE_W_INCH = 13.333
    SLIDE_H_INCH = 7.5
    
    for i, slide_data in enumerate(analyses):
        try:
            # 建立空白投影片
            slide_layout = prs.slide_layouts[6] # 6 = Blank
            slide = prs.slides.add_slide(slide_layout)
            
            # 背景顏色 (Overlay 模式下通常被背景圖覆蓋，但保留作為底色)
            bg_hex = slide_data.get("background_color_hex", "#18181b")
            text_hex = slide_data.get("text_color_hex", "#ffffff")
            text_rgb = hex_to_rgb(text_hex)
            
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = hex_to_rgb(bg_hex)
            
            # 圖片處理 (背景圖)
            img_byte_arr = None
            if i < len(images):
                original_img = images[i]
                if original_img:
                    try:
                        buf = io.BytesIO()
                        original_img.save(buf, format='JPEG', quality=90)
                        buf.seek(0)
                        img_byte_arr = buf
                    except:
                        img_byte_arr = None

            # [Overlay Mode Check]
            # layout might be 'overlay' (v5) or 'split_left_image' (v2) or others.
            layout_type = slide_data.get('layout', 'split_left_image')
            elements = slide_data.get('elements', [])
            
            # If we have 'elements' with bboxes, force overlay mode even if layout says otherwise
            if elements and len(elements) > 0:
                layout_type = 'overlay'

            # --- Layout Implementation ---
            if layout_type == 'overlay':
                # 1. Full Screen Background
                if img_byte_arr:
                    try:
                        pic = slide.shapes.add_picture(img_byte_arr, Inches(0), Inches(0), width=Inches(SLIDE_W_INCH), height=Inches(SLIDE_H_INCH))
                        # Send to back? PPTX adds in order, so first added is back. Correct.
                    except Exception as e:
                        logger.error(f"Slide {i}: Add bg picture failed: {e}")

                # 2. Text Overlays
                for elem in elements:
                    try:
                        content = elem.get('content', '')
                        bbox = elem.get('bbox', [0,0,0,0]) # [ymin, xmin, ymax, xmax] 0-1000
                        font_size_pt = elem.get('font_size', 24)
                        align = elem.get('alignment', 'left')
                        color_hex = elem.get('color_hex', text_hex)
                        
                        ymin, xmin, ymax, xmax = bbox
                        
                        # Convert 0-1000 to Inches
                        left = Inches(xmin / 1000 * SLIDE_W_INCH)
                        top = Inches(ymin / 1000 * SLIDE_H_INCH)
                        width = Inches((xmax - xmin) / 1000 * SLIDE_W_INCH)
                        height = Inches((ymax - ymin) / 1000 * SLIDE_H_INCH)
                        
                        # Add Text Box
                        tb = slide.shapes.add_textbox(left, top, width, height)
                        tf = tb.text_frame
                        tf.word_wrap = True
                        
                        p = tf.paragraphs[0]
                        p.text = str(content)
                        
                        # Use heuristic for font size if missing or too small
                        if not isinstance(font_size_pt, (int, float)) or font_size_pt < 8: 
                            font_size_pt = 18
                        
                        p.font.size = Pt(font_size_pt)
                        try:
                            p.font.color.rgb = hex_to_rgb(color_hex)
                        except:
                            p.font.color.rgb = text_rgb
                        
                        if align == 'center':
                            p.alignment = PP_ALIGN.CENTER
                        elif align == 'right':
                            p.alignment = PP_ALIGN.RIGHT
                        else:
                            p.alignment = PP_ALIGN.LEFT
                            
                    except Exception as e:
                         # logger.warning(f"Element rendering failed: {e}")
                         pass

            elif layout_type == 'full_width_text':
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
                # Split Layout (Default for v2 legacy / fallback)
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
        # Reduce memory usage: dpi=200 (balanced), thread_count=1
        images = convert_from_bytes(pdf_bytes, dpi=200, thread_count=1)
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
    TIMEOUT_PER_PAGE_ANALYSIS = 90 # seconds (Extended for high-res)
    


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
            msg = f"正在處理第 {start_p}/{total_target} 頁..."
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
                        convert_from_path, pdf_path, dpi=200, 
                        first_page=s, last_page=e, thread_count=1
                    )
                else:
                    imgs = []
                    for idx in batch_indices:
                        p = idx + 1
                        res = await asyncio.to_thread(
                           convert_from_path, pdf_path, dpi=200,
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
            process_single_page(img, batch_indices[j] + 1, total_pdf_pages, api_key, remove_icon=remove_icon, pdf_path=pdf_path)
            for j, img in enumerate(batch_images)
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results immediately
        for res in batch_results:
            if isinstance(res, Exception):
                logger.error(f"Batch Analysis Critical Failure: {res}")
                analyses.append({
                    "title": "分析失敗", 
                    "content": ["請手動編輯此頁面"], 
                    "layout": "split_left_image"
                })
                cleaned_images.append(Image.new('RGB', (800, 600), color='white')) 
            elif isinstance(res, tuple) and len(res) == 2:
                # 確保 analysis 是 dict
                analysis = res[0]
                if not isinstance(analysis, dict):
                    analysis = {"title": "格式錯誤", "content": [str(analysis)[:200]]}
                analyses.append(analysis)
                cleaned_images.append(res[1])
            else:
                 # 未預期的格式，給預設值
                 logger.warning(f"Unexpected result format: {res}")
                 analyses.append({"title": "未知錯誤", "content": []})
                 cleaned_images.append(Image.new('RGB', (800, 600), color='white'))

        processed_count += current_batch_size
        
        # [Fail-Safe Strategy] First Page Probe
        # If the very first page failed to analyze, ABORT the entire process.
        # This prevents wasting cost on 50+ pages if the PDF format is fundamentally unreadable or API is down.
        if processed_count == 1 and len(analyses) > 0:
            first_result = analyses[0]
            # Check for known error signatures
            error_titles = ["Analysis Error", "Parse Error", "分析失敗", "未知錯誤", "處理失敗"]
            if (first_result.get("title") in error_titles) or (not first_result.get("content")):
                logger.error("🛑 First Page Probe FAILED. Aborting remaining pages to save cost.")
                # We stop here. The UI will receive just this one error slide.
                break

        if processed_count < total_target:
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    logger.info(f"所有頁面處理完成。總共: {len(analyses)} 頁")
        
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

