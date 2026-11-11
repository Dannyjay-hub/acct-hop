"""Generate assets/acct-hop.icns (a plain placeholder icon). Needs Pillow; run on macOS (uses iconutil)."""
import os, subprocess, tempfile
from PIL import Image, ImageDraw

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((60, 60, S - 60, S - 60), radius=210, fill=(32, 38, 56, 255))
d.rounded_rectangle((60, 60, S - 60, S // 2), radius=210, fill=(44, 52, 78, 255))
d.rectangle((60, 300, S - 60, S // 2), fill=(44, 52, 78, 255))
white = (245, 247, 252, 255)
# two arrows: right on top, left below
def arrow(y, right=True):
    x0, x1 = (230, 800) if right else (224, 794)
    d.rounded_rectangle((x0, y - 38, x1, y + 38), radius=38, fill=white)
    tip = (880, y) if right else (144, y)
    base = 760 if right else 264
    d.polygon([tip, (base, y - 120), (base, y + 120)], fill=white)
arrow(390, True)
arrow(634, False)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "acct-hop.icns")
with tempfile.TemporaryDirectory() as t:
    iconset = os.path.join(t, "acct-hop.iconset")
    os.makedirs(iconset)
    for size in (16, 32, 64, 128, 256, 512):
        img.resize((size, size), Image.LANCZOS).save(os.path.join(iconset, "icon_%dx%d.png" % (size, size)))
        img.resize((size * 2, size * 2), Image.LANCZOS).save(os.path.join(iconset, "icon_%dx%d@2x.png" % (size, size)))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out], check=True)
print("wrote", out)
