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
        def visitor_body(text, cm, tm, fontDict, fontSize):
            if text and text.strip():
                # cm = Current Transformation Matrix
                # tm = Text Matrix
                # We need to calculate the bounding box.
                # pypdf visitor sends: text, current_matrix, text_matrix, font_dict, font_size
                
                # Simplified BBox calculation:
                # x = tm[4], y = tm[5] (bottom-left start)
                # But exact width/height is hard to get perfectly without font metrics in pypdf visitor.
                # However, we can approximate or use a simple point aggregation if using extraction mode.
                
                # Update: pypdf's extract_text(visitor_text=...) is easier but gives less granular control per block?
                # Actually, implementing a custom visitor is better for coordinates.
                
                # For this 'visitor_body', we get individual operations.
                # x = tm[4]
                # y = tm[5]
                # This is just the starting point. Calculating width is non-trivial without precise font width tables.
                
                # ALTERNATIVE STRATEGY:
                # Use page.extract_text(orientations=(0, 90, 180, 270)) for raw text string.
                # BUT we need COORDINATES for masking.
                
                # Let's use a simple heuristic for now or strict visitor if possible.
                # Since pypdf doesn't give easy bbox in visitor, maybe we just store the operation?
                
                # Actually, let's look at `extract_words` from pdfplumber? 
                # Requirement said "Use pypdf". 
                # pypdf added `visitor_text` callback.
                
                # Let's try to capture x, y. Valid width/height might be tricky.
                # We can assume a standard height based on fontSize.
                # Width is length of text * fontSize * 0.5 (rough approx) if we can't get it.
                # But for masking, we want to be generous.
                
                x = tm[4]
                y = tm[5]
                
                # Rough BBox approximation
                # Height is usually fontSize
                height = fontSize if fontSize else 12
                # Width approx
                width = len(text) * (fontSize if fontSize else 12) * 0.6 
                
                # Note: PDF coords (0,0) is usually bottom-left. 
                # PIL Image coords (0,0) is top-left.
                # We will need page mediaBox to flip Y.
                
                results.append({
                    'text': text,
                    'bbox_pdf': (x, y, x + width, y + height), # PDF Coords (Bottom-Left Origin usually)
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
