from PIL import Image
from collections import Counter
import sys

try:
    img_path = '/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/docs/images/Hybrid-RAG-512.png'
    img = Image.open(img_path)
    img = img.convert('RGB')
    img = img.resize((50, 50))
    pixels = list(img.getdata())
    
    # Simple color quantization and finding the most common non-white/black color
    counter = Counter(pixels)
    most_common = counter.most_common(10)
    
    brand_color = None
    max_saturation = -1

    for color, count in most_common:
        r, g, b = color
        # Skip white-ish and black-ish
        if sum(color) > 700 or sum(color) < 50:
            continue
            
        # Calculate saturation
        mx = max(r, g, b)
        mn = min(r, g, b)
        sat = (mx - mn) / (mx + 1e-5)
        
        if sat > max_saturation:
            max_saturation = sat
            brand_color = color

    if brand_color:
        print(f'#{brand_color[0]:02x}{brand_color[1]:02x}{brand_color[2]:02x}')
    else:
        print('#4F46E5') # Default fallback

except Exception as e:
    print(f'Error: {e}')
    print('#4F46E5')

