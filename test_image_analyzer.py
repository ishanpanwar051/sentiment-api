from model.image_analyzer import get_image_analyzer
from PIL import Image, ImageDraw
import io

# Create a simple test image (a smiley face)
img = Image.new('RGB', (200, 200), color='white')
draw = ImageDraw.Draw(img)
# Draw eyes
draw.ellipse((50, 60, 70, 80), fill='black')
draw.ellipse((130, 60, 150, 80), fill='black')
# Draw a smile
draw.arc((50, 100, 150, 160), start=0, end=180, fill='black', width=5)

# Save to bytes
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='JPEG')
img_byte_arr = img_byte_arr.getvalue()

print("Testing ImageAnalyzer...")
analyzer = get_image_analyzer()
print("Calling analyze_frame...")
result = analyzer.analyze_frame(img_byte_arr)
print(f"Result: {result}")
print("✓ Test passed!")
