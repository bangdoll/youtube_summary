from pytubefix import YouTube

# Init without po_token arg
yt = YouTube("https://www.youtube.com/watch?v=dQw4w9WgXcQ", use_po_token=True)

print("Has po_token property?", hasattr(yt, 'po_token'))
print("Has visitor_data property?", hasattr(yt, 'visitor_data'))
# Check if they are settable (not read-only) -> by trying to set them
try:
    yt.po_token = "TEST_TOKEN"
    print("Successfully set po_token")
except Exception as e:
    print(f"Failed to set po_token: {e}")

try:
    yt.visitor_data = "TEST_VISITOR"
    print("Successfully set visitor_data")
except Exception as e:
    print(f"Failed to set visitor_data: {e}")
