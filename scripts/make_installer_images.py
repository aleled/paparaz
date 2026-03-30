"""Generate branded Inno Setup wizard images for the PapaRaZ installer.

Outputs:
  installer/wizard_side.bmp  — 164x314 px  (Welcome / Finish page left panel)
  installer/wizard_small.bmp — 55x58 px    (inner pages top-right)
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "installer"
OUT_DIR.mkdir(exist_ok=True)

# ── brand palette ──────────────────────────────────────────────
BG        = (19, 19, 31)       # #13131f
PURPLE    = (116, 0, 150)      # #740096
PURPLE_LT = (192, 63, 221)     # #c03fdd
DIVIDER   = (58, 58, 78)       # #3a3a4e
WHITE     = (255, 255, 255)
GREY_LT   = (200, 200, 220)
GREY_MID  = (140, 140, 170)
GREY_DK   = (70,  70,  95)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Try a bold/regular Windows font, fall back to default."""
    candidates = {
        "bold":    ["C:/Windows/Fonts/arialbd.ttf",  "C:/Windows/Fonts/calibrib.ttf"],
        "regular": ["C:/Windows/Fonts/arial.ttf",    "C:/Windows/Fonts/calibri.ttf"],
        "light":   ["C:/Windows/Fonts/ariali.ttf",   "C:/Windows/Fonts/arial.ttf"],
    }
    for path in candidates.get(name, candidates["regular"]):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _draw_logo_circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int):
    """Purple circle with white 'P' — the app logo placeholder."""
    # Outer glow
    for offset in range(4, 0, -1):
        alpha = int(60 * (1 - offset / 5))
        draw.ellipse(
            [cx - r - offset, cy - r - offset, cx + r + offset, cy + r + offset],
            outline=(*PURPLE, alpha),
        )
    # Fill
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PURPLE)
    # Highlight arc (top-left)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 outline=PURPLE_LT, width=2)
    # "P" letter
    font = _font("bold", r)
    draw.text((cx, cy + 1), "P", fill=WHITE, font=font, anchor="mm")


# ── wizard_side.bmp  164 × 314 ─────────────────────────────────
def make_side(version: str = ""):
    W, H = 164, 314
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Gradient stripe at the very top
    for y in range(60):
        t = 1.0 - y / 60
        r2 = int(BG[0] + (PURPLE[0] - BG[0]) * t)
        g2 = int(BG[1] + (PURPLE[1] - BG[1]) * t)
        b2 = int(BG[2] + (PURPLE[2] - BG[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r2, g2, b2))

    # Logo circle
    _draw_logo_circle(draw, cx=W // 2, cy=58, r=28)

    # App name
    draw.text((W // 2, 102), "PapaRaZ",
              fill=GREY_LT, font=_font("bold", 20), anchor="mm")

    # Tag line
    draw.text((W // 2, 121), "Screen Capture",
              fill=GREY_MID, font=_font("regular", 10), anchor="mm")
    draw.text((W // 2, 133), "& Annotation",
              fill=GREY_MID, font=_font("regular", 10), anchor="mm")

    # Divider
    draw.line([(18, 148), (W - 18, 148)], fill=PURPLE, width=1)

    # Feature bullets
    features = [
        "✦  Instant capture",
        "✦  Object-based edits",
        "✦  Stamps & arrows",
        "✦  Crop & slice",
        "✦  OCR recognition",
        "✦  One-click share",
    ]
    f_font = _font("regular", 9)
    y0 = 162
    for line in features:
        draw.text((22, y0), line, fill=GREY_DK, font=f_font)
        y0 += 16

    # Bottom divider
    draw.line([(18, H - 26), (W - 18, H - 26)], fill=DIVIDER, width=1)

    # Version tag
    ver_text = f"v{version}" if version else ""
    draw.text((W // 2, H - 12), ver_text,
              fill=GREY_DK, font=_font("regular", 8), anchor="mm")

    path = OUT_DIR / "wizard_side.bmp"
    img.save(path, "BMP")
    print(f"  wrote {path.relative_to(ROOT)}")


# ── wizard_small.bmp  55 × 58 ──────────────────────────────────
def make_small():
    W, H = 55, 58
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    _draw_logo_circle(draw, cx=W // 2, cy=H // 2 - 1, r=22)
    path = OUT_DIR / "wizard_small.bmp"
    img.save(path, "BMP")
    print(f"  wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    # Optionally accept version as first CLI arg
    ver = sys.argv[1] if len(sys.argv) > 1 else "0.9.1"
    print("Generating installer wizard images...")
    make_side(ver)
    make_small()
    print("Done.")
