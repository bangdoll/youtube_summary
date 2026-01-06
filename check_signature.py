import inspect
from pytubefix import YouTube

sig = inspect.signature(YouTube.__init__)
print("YouTube.__init__ parameters:")
for name, param in sig.parameters.items():
    print(f"- {name}")

print("\nDoes it have 'po_token'?", 'po_token' in sig.parameters)
print("Does it have 'use_po_token'?", 'use_po_token' in sig.parameters)
