import logging
from typing import List, Dict, Tuple, Optional
import pypdf

# Config Logger
logger = logging.getLogger(__name__)

def extract_text_and_coordinates(pdf_path: str, page_index: int) -> List[Dict]:
    """
    Extracts text and coordinates from a specific page of a PDF using pypdf.
    
    Args:
        pdf_path: Path to the PDF file.
        page_index: Index of the page to extract (0-based).
        
    Returns:
        List of dictionaries containing 'text' and 'bbox' (x0, y0, x1, y1).
        Coordinates are in PDF Point units (usually 1/72 inch).
        Returns None or empty list if no text found.
    """
    results = []

    try:
        reader = pypdf.PdfReader(pdf_path)
        if page_index >= len(reader.pages):
            logger.error(f"Page index {page_index} out of range for {pdf_path}")
            return []

        page = reader.pages[page_index]
        
        # Visitor function to extract text and matrix
        # 使用 *args 接收參數，避免 pypdf 版本差異導致的簽名問題
        def visitor_body(text, cm, tm, fontDict=None, fontSize=None, *args, **kwargs):
            if text and text.strip():
                # cm = Current Transformation Matrix
                # tm = Text Matrix
                x = tm[4]
                y = tm[5]
                
                # Rough BBox approximation
                # Height is usually fontSize (default 12 if not provided)
                height = fontSize if fontSize else 12
                # Width approx
                width = len(text) * height * 0.6 
                
                # PDF coords (0,0) is usually bottom-left. 
                # PIL Image coords (0,0) is top-left.
                
                results.append({
                    'text': text,
                    'bbox_pdf': (x, y, x + width, y + height),
                    'tm': tm,
                    'font_size': fontSize
                })

        # Run extraction
        page.extract_text(visitor_operand_before=visitor_body)
        
        # Post-process to normalize coordinates to Top-Left Origin (for Image Masking)
        # mediabox = page.mediabox
        # page_height = float(mediabox.height)
        
        # final_results = []
        # for item in results:
        #     x0, y0_pdf, x1, y1_pdf = item['bbox_pdf']
        #     # Flip Y
        #     y0 = page_height - y1_pdf
        #     y1 = page_height - y0_pdf
        #     final_results.append({
        #         'text': item['text'],
        #         'bbox': (x0, y0, x1, y1)
        #     })
            
        return results

    except Exception as e:
        logger.error(f"Native PDF Extraction Error: {e}")
        return []

def get_page_size(pdf_path: str, page_index: int) -> Tuple[float, float]:
    """Returns (width, height) in points."""
    try:
        reader = pypdf.PdfReader(pdf_path)
        page = reader.pages[page_index]
        return (float(page.mediabox.width), float(page.mediabox.height))
    except:
        return (0, 0)
