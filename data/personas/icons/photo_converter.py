import os
from PIL import Image

INPUT_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
OUTPUT_FORMAT = 'webp'

os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def convert_image(input_path, output_path, size=(640, 640)):
    try:
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            elif img.mode not in ('RGB',):
                img = img.convert('RGB')

            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            img = img.resize(size, Image.Resampling.LANCZOS)

            if OUTPUT_FORMAT == 'webp':
                img.save(output_path, 'WEBP', quality=85, method=6)
            else:
                img.save(output_path, 'JPEG', quality=85, optimize=True)

            print(f"✅ {os.path.basename(input_path)} → {output_path}")
            return True
    except Exception as e:
        print(f"❌ Error with {input_path}: {e}")
        return False

supported_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')
image_files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(supported_extensions)]

converted = 0
for img_file in image_files:
    input_path = os.path.join(INPUT_FOLDER, img_file)
    name_without_ext = os.path.splitext(img_file)[0]
    ext = '.webp' if OUTPUT_FORMAT == 'webp' else '.jpg'
    output_path = os.path.join(OUTPUT_FOLDER, f"{name_without_ext}{ext}")

    if convert_image(input_path, output_path):
        converted += 1
        os.remove(input_path)

print(f"\nCompleted: {converted}/{len(image_files)} images in '{OUTPUT_FOLDER}'")