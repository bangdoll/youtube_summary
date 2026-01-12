
import asyncio
from slide_generator import create_pptx_from_analysis
from PIL import Image, ImageDraw

def test_overlay_generation():
    print("Testing v5.0 Overlay Layout Generation...")
    
    # 1. Create Dummy Background Image
    bg_img = Image.new('RGB', (1333, 750), color=(50, 50, 50))
    d = ImageDraw.Draw(bg_img)
    d.rectangle([100, 100, 400, 400], fill=(200, 50, 50)) # Red box on BG
    
    images = [bg_img]
    
    # 2. Mock Analysis Result with Elements
    analysis = {
        "title": "v5.0 Overlay Test",
        "background_color_hex": "#323232",
        "text_color_hex": "#FFFFFF",
        "layout": "overlay",
        "elements": [
            {
                "content": "Title Overlay (Top Left)",
                "bbox": [50, 50, 150, 500], # ymin, xmin, ymax, xmax (0-1000)
                "font_size": 36,
                "color_hex": "#FFFFFF",
                "alignment": "left"
            },
            {
                "content": "Body Text Overlay (Center)",
                "bbox": [200, 300, 800, 800],
                "font_size": 18,
                "color_hex": "#00FF00",
                "alignment": "center"
            }
        ]
    }
    
    analyses = [analysis]
    output_path = "v5_overlay_test.pptx"
    
    try:
        create_pptx_from_analysis(analyses, images, output_path)
        print(f"Success! Generated {output_path}")
    except Exception as e:
        print(f"Generation Failed: {e}")

if __name__ == "__main__":
    test_overlay_generation()
