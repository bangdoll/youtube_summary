from PIL import Image, ImageDraw
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

def create_masked_image(
    original_image: Image.Image, 
    text_data: List[Dict], 
    pdf_width_pts: float, 
    pdf_height_pts: float,
    mask_color: Tuple[int, int, int] = (255, 0, 255) # Magenta for easy detection
) -> Image.Image:
    """
    Draws masks over extracted text regions on the original image.
    
    Args:
        original_image: The PIL Image converted from PDF.
        text_data: List of dicts with 'bbox_pdf' (x0, y0, x1, y1) in PDF Points.
        pdf_width_pts: Width of the PDF page in points.
        pdf_height_pts: Height of the PDF page in points.
        mask_color: RGB tuple for the mask color.
        
    Returns:
        A copy of the image with masks drawn.
    """
    if not text_data:
        return original_image.copy()

    # Create a copy to draw on
    masked_img = original_image.copy()
    draw = ImageDraw.Draw(masked_img)
    
    img_width, img_height = original_image.size
    
    # Calculate Scale Factors
    # Image might be 1600px (resized) or 3000px (raw).
    # PDF is usually e.g. 595.28 pts (A4).
    scale_x = img_width / pdf_width_pts
    scale_y = img_height / pdf_height_pts
    
    try:
        for item in text_data:
            # bbox_pdf is (x0, y0, x1, y1) - usually Bottom-Left Origin in PDF raw extraction
            # BUT check native_pdf.py visitor implementation.
            # tm[5] (y) in PDF is distance from bottom.
            # So y=0 is bottom.
            
            x0_pdf, y0_pdf_raw, x1_pdf, y1_pdf_raw = item['bbox_pdf']
            
            # Convert PDF Bottom-Left to Image Top-Left
            # PDF Y increases Upwards. Image Y increases Downwards.
            # correct_y = page_height - pdf_y
            
            # x coords scale processing
            x0 = x0_pdf * scale_x
            x1 = x1_pdf * scale_x
            
            # y coords processing (Flip)
            # PDF y0 is the bottom of the text (start point).
            # PDF y1 is the top of the text (y0 + height).
            
            # Image y corresponding to PDF y1 (Top of text) is:
            y_top = (pdf_height_pts - y1_pdf_raw) * scale_y
            
            # Image y corresponding to PDF y0 (Bottom of text) is:
            y_bottom = (pdf_height_pts - y0_pdf_raw) * scale_y
            
            # Ensure coordinates are ordered for PIL (x0, y0, x1, y1) -> (left, top, right, bottom)
            rect = [
                x0 - 5,          # Padding Left
                y_top - 5,       # Padding Top (Top is smaller Y in image)
                x1 + 10,         # Padding Right (Generous)
                y_bottom + 5     # Padding Bottom
            ]
            
            # Draw Rectangle
            draw.rectangle(rect, fill=mask_color, outline=mask_color)
            
        return masked_img
        
    except Exception as e:
        logger.error(f"Masking Error: {e}")
        return original_image
