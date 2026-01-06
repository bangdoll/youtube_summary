from pytubefix import YouTube
try:
    # Initialize with use_po_token=True. This should trigger the node generation if supported.
    yt = YouTube("https://www.youtube.com/watch?v=dQw4w9WgXcQ", use_po_token=True)
    
    # Introspect to find the token
    # It might be in private attributes or just not exposed easily.
    print(f"Checking object attributes...")
    if hasattr(yt, 'po_token'):
        print(f"PO_TOKEN: {yt.po_token}")
    if hasattr(yt, 'visitor_data'):
        print(f"VISITOR_DATA: {yt.visitor_data}")
        
    # Check internal API if known (often _po_token or similar)
except Exception as e:
    print(f"Error: {e}")
