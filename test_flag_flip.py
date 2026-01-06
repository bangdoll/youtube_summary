from pytubefix import YouTube

yt = YouTube("https://www.youtube.com/watch?v=dQw4w9WgXcQ", use_po_token=False)

print(f"Initial use_po_token: {yt.use_po_token}")

try:
    yt.use_po_token = True
    print(f"Successfully set use_po_token to: {yt.use_po_token}")
except Exception as e:
    print(f"Failed to set use_po_token: {e}")

try:
    # Also check assuming internal attribute if property fails
    yt._use_po_token = True
    print(f"Successfully set _use_po_token to: {yt._use_po_token}")
except Exception as e:
    print(f"Failed to set _use_po_token: {e}")
