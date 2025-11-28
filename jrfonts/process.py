import os
from PIL import Image

def process_images(input_folder):
    # Create output subfolders
    fill_folder = os.path.join(input_folder, "fill")
    shadow_folder = os.path.join(input_folder, "shadow")
    os.makedirs(fill_folder, exist_ok=True)
    os.makedirs(shadow_folder, exist_ok=True)

    # Loop through all PNG files
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".png"):
            filepath = os.path.join(input_folder, filename)
            img = Image.open(filepath).convert("RGBA")
            pixels = img.load()

            # Create copies for fill and shadow
            fill_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
            shadow_img = img.copy()
            shadow_pixels = shadow_img.load()

            for y in range(img.height):
                for x in range(img.width):
                    r, g, b, a = pixels[x, y]

                    # Check if pixel is fully white
                    if (r, g, b) == (255, 255, 255) and a > 0:
                        # Fill version: keep white pixel, else transparent
                        fill_img.putpixel((x, y), (255, 255, 255, a))
                        # Shadow version: replace white with black
                        shadow_pixels[x, y] = (0, 0, 0, a)
                    else:
                        # Fill version: transparent
                        fill_img.putpixel((x, y), (0, 0, 0, 0))

            # Save results
            fill_img.save(os.path.join(fill_folder, filename))
            shadow_img.save(os.path.join(shadow_folder, filename))

    print("Processing complete! Check 'fill' and 'shadow' subfolders.")

process_images(".")
