from pytubefix import YouTube
from pytubefix.proof_of_origin import generate_po_token_nodes

try:
    # Attempt to generate token using pytubefix's internal node wrapper
    # Note: internal APIs might change, this is a best guess based on common pytubefix usage for po_token
    # If this fails, we will just use a real request
    
    # We can also just fetch a video and see if we can extract it from internal state
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    # pytubefix 2.x+ handles po_token automatically if node is present.
    # We want to EXTRACT it to show the user.
    
    # Let's try to invoke the generator directly if possible
    # Based on source code analysis of pytubefix (mental model):
    token_object = generate_po_token_nodes()
    print("Successfully generated PO Token details:")
    print(f"PO_TOKEN: {token_object['po_token']}")
    print(f"VISITOR_DATA: {token_object['visitor_data']}")
    
except Exception as e:
    print(f"Error generating token directly: {e}")
    # Fallback: Just print instructions if direct access fails
