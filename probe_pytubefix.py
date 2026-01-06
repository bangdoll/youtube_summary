from pytubefix import YouTube

yt = YouTube("https://www.youtube.com/watch?v=dQw4w9WgXcQ", use_po_token=True)

print("Has _po_token?", hasattr(yt, '_po_token'))
print("Has _visitor_data?", hasattr(yt, '_visitor_data'))

try:
    yt._po_token = "TEST_TOKEN"
    print("Successfully set _po_token")
except Exception as e:
    print(f"Failed to set _po_token: {e}")
    
try:
    yt._visitor_data = "TEST_VISITOR"
    print("Successfully set _visitor_data")
except Exception as e:
    print(f"Failed to set _visitor_data: {e}")
