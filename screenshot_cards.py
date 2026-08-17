import subprocess
import json
import time
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML_FILE = Path(__file__).parent / "share-cards.html"
OUTPUT_DIR = Path(__file__).parent / "share-cards-png"
OUTPUT_DIR.mkdir(exist_ok=True)

CARD_NAMES = [
    "00_cover", "01_media", "02_structure", "03_hook",
    "04_rhythm", "05_character", "06_dialogue", "07_shots",
    "08_composition", "09_montage", "10_transition_sound", "11_storyboard",
]

JS_TEMPLATE = """
(async () => {
  const cards = document.querySelectorAll('.card');
  const results = [];
  for (let i = 0; i < cards.length; i++) {
    const rect = cards[i].getBoundingClientRect();
    results.push({
      index: i,
      top: Math.round(rect.top),
      left: Math.round(rect.left),
      width: Math.round(rect.width),
      height: Math.round(rect.height)
    });
  }
  return JSON.stringify(results);
})()
"""

# Step 1: Get card dimensions via Chrome headless with DevTools protocol
# We'll use a simpler approach - screenshot each card individually by creating temp HTML files

# Actually, let's use Chrome's --screenshot with a specific element screenshot via CDP
# The simplest reliable approach: use Chrome headless to take full page screenshot,
# then crop with Python PIL

# Step 1: Take full page screenshot
full_png = OUTPUT_DIR / "_full_page.png"
print("Taking full page screenshot...")

# Chrome headless needs the file URL
file_url = f"file://{HTML_FILE}"

# Use Chrome headless with specific window size and screenshot
# We need to set a large window to capture all cards
cmd = [
    CHROME,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
    f"--screenshot={full_png}",
    "--window-size=1080,17000",
    "--force-device-scale-factor=2",
    file_url,
]
subprocess.run(cmd, capture_output=True, timeout=60)
print(f"Full page screenshot saved: {full_png} (exists: {full_png.exists()})")

if not full_png.exists():
    print("ERROR: Full page screenshot failed")
    exit(1)

# Step 2: Get card positions by running JS in Chrome
# We'll use a simpler approach - calculate positions based on card structure
# Each card is 1080px wide, aspect ratio 4:5 = 1350px tall, with 2.5rem (40px) margin
# With device scale factor 2, each card is 2160x2700 pixels in the screenshot

# Let's use Python PIL to crop
try:
    from PIL import Image
except ImportError:
    subprocess.run(["pip3", "install", "Pillow"], capture_output=True, timeout=60)
    from PIL import Image

img = Image.open(full_png)
print(f"Full image size: {img.size}")

# The page has body padding 2rem (32px) top and 1rem (16px) sides
# Cards are max-width 1080px, centered
# With scale factor 2, multiply everything by 2
scale = 2
body_padding_top = 32 * scale
body_padding_sides = 16 * scale
card_margin_bottom = 40 * scale  # 2.5rem

# Card width = min(1080px, viewport_width - 2*16px) 
# With viewport 1080px, card width = 1080 - 32 = 1048px (but max-width is 1080px)
# Actually the card has width: 1080px; max-width: 100%
# With viewport 1080px, the card takes full width minus padding

# Let's calculate based on actual image dimensions
img_width, img_height = img.size
print(f"Image dimensions: {img_width}x{img_height}")

# With window-size=1080 and scale=2, the image should be 2160px wide
# Cards are centered with padding
# Let's crop each card region

# Approximate card height = 1080 * 5/4 = 1350px at 1x, so 2700px at 2x
# But we need to account for the actual rendered size

# Let's try a different approach - detect card boundaries by looking for the card borders
# For now, let's calculate based on known structure

# The .card elements have: width 1080px (max-width 100%), aspect-ratio 4/5
# In a 1080px viewport with 16px padding each side, available width = 1048px
# So card width = 1048px, card height = 1048 * 5/4 = 1310px
# At scale 2: card width = 2096px, card height = 2620px

# Actually, let's be more precise by using a detection script
# Write a detection HTML that outputs card positions as JSON

detect_html = HTML_FILE.parent / "_detect.html"
detect_html.write_text(f"""
<!DOCTYPE html>
<html><head><script>
window.onload = function() {{
  const cards = document.querySelectorAll('.card');
  const data = [];
  let totalHeight = 0;
  for (let i = 0; i < cards.length; i++) {{
    const rect = cards[i].getBoundingClientRect();
    data.push({{i: i, top: rect.top + window.scrollY, left: rect.left, width: rect.width, height: rect.height}});
  }}
  document.title = JSON.stringify(data);
}};
</script></head>
<body><iframe src="{HTML_FILE.name}" style="width:1080px;height:100vh;border:none;"></iframe></body></html>
""")

# Actually, let's just use the simpler approach:
# The screenshot was taken with window-size=1080
# Cards are displayed as block elements, width 1080px (max-width 100%)
# With body padding 2rem 1rem = 32px top/bottom, 16px left/right
# So card content width = 1080 - 32 = 1048px

# At scale 2:
# body padding left = 32px (16*2)
# body padding top = 64px (32*2)  
# card width = 2096px (1048*2)
# card height = 2620px (1310*2) -- but aspect-ratio 4/5 means height = width * 5/4
# card width 1048 -> height 1310
# At 2x: 2096 x 2620
# card margin-bottom = 80px (40*2)

# Let's calculate and crop
card_w_1x = 1048  # 1080 - 32 padding
card_h_1x = int(card_w_1x * 5 / 4)  # 1310
card_w = card_w_1x * scale  # 2096
card_h = card_h_1x * scale  # 2620
card_margin = 40 * scale  # 80
body_pad_top = 32 * scale  # 64
body_pad_left = 16 * scale  # 32

print(f"Calculated card size: {card_w}x{card_h}")
print(f"Body padding: top={body_pad_top}, left={body_pad_left}")

# Crop each card
for i, name in enumerate(CARD_NAMES):
    y_offset = body_pad_top + i * (card_h + card_margin)
    # Clamp to image bounds
    y_end = min(y_offset + card_h, img_height)
    x_end = min(body_pad_left + card_w, img_width)
    
    crop_box = (body_pad_left, y_offset, x_end, y_end)
    cropped = img.crop(crop_box)
    
    # Resize to standard 1080x1350 for social media
    cropped = cropped.resize((1080, 1350), Image.LANCZOS)
    
    out_path = OUTPUT_DIR / f"{name}.png"
    cropped.save(out_path, "PNG", optimize=True)
    print(f"Saved: {out_path} ({cropped.size})")

# Clean up full page screenshot
full_png.unlink()
print(f"\nDone! {len(CARD_NAMES)} PNG files saved to {OUTPUT_DIR}")
