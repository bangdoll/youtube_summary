import asyncio
import io
import time
from PIL import Image
import logging

# Mock logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_stability")

# Mock Configuration
TIMEOUT_PER_PAGE_ANALYSIS = 10

# Create a huge dummy image (3000x3000) simulating 200 DPI source
original_image = Image.new('RGB', (3000, 3000), color='white')

async def mock_analyze_slide(image, api_key):
    # Simulate processing time
    await asyncio.sleep(0.5)
    width, height = image.size
    print(f"[Analysis] Input Image Size: {width}x{height}")
    if width <= 1024 and height <= 1024:
        print("[Analysis] ✅ CORRECT: Image is resized to <= 1024px")
    else:
        print("[Analysis] ❌ ERROR: Image is too large!")
    return {"title": "Mock Title"}

async def mock_remove_text(image, api_key, remove_icon=False):
    # Simulate processing time
    await asyncio.sleep(0.5)
    width, height = image.size
    print(f"[Text Removal] Input Image Size: {width}x{height}")
    if width <= 1600 and height <= 1600 and width > 1024:
        print("[Text Removal] ✅ CORRECT: Image is resized to <= 1600px (High Quality)")
    elif width <= 1024:
        print("[Text Removal] ⚠️ WARNING: Image might be too small for quality edit?")
    else:
        print("[Text Removal] ❌ ERROR: Image is too large!")
    return image

# Function duplicating the logic in slide_generator.py (v2.10.23)
async def process_single_page(img, page_num, total):
    print(f"\n--- Processing Page {page_num}/{total} ---")
    start_time = time.time()
    
    # 1. Prepare Content for Analysis
    # Optimize for Analysis Speed: 1024px
    img_analysis = img.copy()
    img_analysis.thumbnail((1024, 1024))
    
    # 2. Prepare Content for Text Removal
    # Optimize for Quality: 1600px
    img_removal = img.copy()
    img_removal.thumbnail((1600, 1600))
    
    try:
        # SEQUENTIAL EXECUTION SIMULATION
        print("[System] Starting Analysis...")
        analysis_result = await mock_analyze_slide(img_analysis, "dummy_key")
        
        print("[System] Analysis Done. Starting Text Removal...")
        cleaned_image = await mock_remove_text(img_removal, "dummy_key", remove_icon=False)
        
        print("[System] All Done.")
        return analysis_result, cleaned_image
        
    except Exception as e:
        print(f"Error: {e}")

async def main():
    print("=== Stability Logic Verification ===")
    print(f"Original Image: {original_image.size}")
    
    # Run the process
    await process_single_page(original_image, 1, 1)

if __name__ == "__main__":
    asyncio.run(main())
