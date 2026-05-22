import os
from PIL import Image, ImageOps

directory = r"d:\Python Coding\Liberator\plugin.video.liberator\resources\media\icons"

# Color to tint: purple/magenta (R=170, G=0, B=255)
tint_color = (170, 0, 255)

for filename in os.listdir(directory):
    if filename.endswith(".png"):
        filepath = os.path.join(directory, filename)
        try:
            img = Image.open(filepath).convert("RGBA")
            # Extract alpha channel
            r, g, b, alpha = img.split()
            # Convert to grayscale
            gray = img.convert('L')
            # Colorize grayscale using tint color
            colored = ImageOps.colorize(gray, black="black", white=tint_color)
            # Add back alpha channel
            colored.putalpha(alpha)
            colored.save(filepath)
            print(f"Colorized {filename}")
        except Exception as e:
            print(f"Error on {filename}: {e}")
