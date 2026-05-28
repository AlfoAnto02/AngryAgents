import os
from PIL import Image


INPUT_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
OUTPUT_FORMAT = 'webp' 


os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def convert_image(input_path, output_path, size=(320, 320)):
    try:
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            elif img.mode not in ('RGB',):
                img = img.convert('RGB')


            img.thumbnail(size, Image.Resampling.LANCZOS)


            square = Image.new('RGB', size, (255, 255, 255))
            left = (size[0] - img.width) // 2
            top = (size[1] - img.height) // 2
            square.paste(img, (left, top))


            if OUTPUT_FORMAT == 'webp':
                square.save(output_path, 'WEBP', quality=85, method=6)
            else:
                square.save(output_path, 'JPEG', quality=85, optimize=True)


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