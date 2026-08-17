import subprocess
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML_FILE = Path(__file__).parent / "share-cards-v2.html"
OUTPUT_DIR = Path(__file__).parent / "share-cards-png-v2"
OUTPUT_DIR.mkdir(exist_ok=True)

CARD_NAMES = [
    "00_cover",
    "01_script_basics",
    "02_hook_rhythm",
    "03_character_dialogue",
    "04_visual_grammar",
    "05_editing_production",
]

full_png = OUTPUT_DIR / "_full_page.png"
print("Taking full page screenshot...")

file_url = f"file://{HTML_FILE}"
cmd = [
    CHROME,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
    f"--screenshot={full_png}",
    "--window-size=1080,9000",
    "--force-device-scale-factor=2",
    file_url,
]
subprocess.run(cmd, capture_output=True, timeout=60)
print(f"Full page screenshot: {full_png.exists()}")

if not full_png.exists():
    print("ERROR: screenshot failed")
    exit(1)

from PIL import Image

img = Image.open(full_png)
print(f"Full image: {img.size}")

scale = 2
body_pad_top = 32 * scale  # 64
body_pad_left = 16 * scale  # 32
card_margin = 40 * scale     # 80

card_w_1x = 1048  # 1080 - 32
card_h_1x = int(card_w_1x * 5 / 4)  # 1310
card_w = card_w_1x * scale  # 2096
card_h = card_h_1x * scale  # 2620

img_width, img_height = img.size
print(f"Image: {img_width}x{img_height}, Card: {card_w}x{card_h}")

for i, name in enumerate(CARD_NAMES):
    y_offset = body_pad_top + i * (card_h + card_margin)
    y_end = min(y_offset + card_h, img_height)
    x_end = min(body_pad_left + card_w, img_width)

    crop_box = (body_pad_left, y_offset, x_end, y_end)
    cropped = img.crop(crop_box)
    cropped = cropped.resize((1080, 1350), Image.LANCZOS)

    out_path = OUTPUT_DIR / f"{name}.png"
    cropped.save(out_path, "PNG", optimize=True)
    print(f"Saved: {out_path} ({cropped.size})")

full_png.unlink()
print(f"\nDone! {len(CARD_NAMES)} PNG files saved to {OUTPUT_DIR}")
