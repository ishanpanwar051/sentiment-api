import requests
from PIL import Image, ImageDraw
import io

# Create a simple test image
img = Image.new('RGB', (200, 200), color='white')
draw = ImageDraw.Draw(img)
draw.ellipse((50, 60, 70, 80), fill='black')
draw.ellipse((130, 60, 150, 80), fill='black')
draw.arc((50, 100, 150, 160), start=0, end=180, fill='black', width=5)

img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='JPEG')
img_bytes = img_byte_arr.getvalue()

url = "http://localhost:8000/api/analyze-frame"
files = {"file": ("frame.jpg", img_bytes, "image/jpeg")}

print("Calling /api/analyze-frame...")
response = requests.post(url, files=files)
print(f"Status code: {response.status_code}")
print(f"Response: {response.json()}")
