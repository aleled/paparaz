"""Generate GitHub social preview image (1280x640) and README banner (900x180)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

BG       = (13, 13, 25)
PURPLE   = (116, 0, 150)
PURPLE_L = (192, 63, 221)
WHITE    = (255, 255, 255)
GREY_L   = (210, 210, 230)
GREY_M   = (140, 140, 170)


def _font(name, size):
    candidates = {
        "bold":    ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf"],
        "regular": ["C:/Windows/Fonts/arial.ttf",   "C:/Windows/Fonts/calibri.ttf"],
    }
    for p in candidates.get(name, candidates["regular"]):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _logo_circle(draw, cx, cy, r):
    for off in range(5, 0, -1):
        a = int(40 * (1 - off / 6))
        draw.ellipse([cx-r-off, cy-r-off, cx+r+off, cy+r+off], outline=(*PURPLE, a))
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=PURPLE)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=PURPLE_L, width=2)
    draw.text((cx, cy+1), "P", fill=WHITE, font=_font("bold", r), anchor="mm")


def make_social(out_path: Path, w=1280, h=640):
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)

    # Purple gradient left band
    for x in range(320):
        t = 1 - x / 320
        r2 = int(PURPLE[0] * t * 0.6)
        g2 = int(PURPLE[1] * t * 0.6)
        b2 = int(PURPLE[2] * t * 0.6 + BG[2] * (1-t))
        draw.line([(x, 0), (x, h)], fill=(r2, g2, b2))

    # Dot grid (right side, subtle)
    for gx in range(340, w, 36):
        for gy in range(0, h, 36):
            draw.ellipse([gx-1, gy-1, gx+1, gy+1], fill=(30, 30, 50))

    # Horizontal accent line
    draw.line([(0, h//2 - 1), (w, h//2 - 1)], fill=(40, 0, 55), width=1)

    # Logo circle
    _logo_circle(draw, cx=160, cy=h//2, r=64)

    # Title
    draw.text((300, h//2 - 60), "PapaRaZ",
              fill=WHITE, font=_font("bold", 96), anchor="lm")

    # Tagline
    draw.text((304, h//2 + 46),
              "Screen Capture & Annotation  ·  Windows",
              fill=GREY_M, font=_font("regular", 28), anchor="lm")

    # Feature pills
    pills = ["✦ Stamps", "✦ OCR", "✦ Crop", "✦ Blur", "✦ Arrows", "✦ Multi-select"]
    px, py = 304, h//2 + 108
    for pill in pills:
        tw = draw.textlength(pill, font=_font("regular", 18))
        pad = 12
        draw.rounded_rectangle([px-pad, py-12, px+tw+pad, py+14],
                                radius=10, fill=(30, 0, 45), outline=PURPLE)
        draw.text((px, py+1), pill, fill=GREY_L, font=_font("regular", 18))
        px += tw + pad*2 + 8

    # Bottom right version tag
    draw.text((w - 20, h - 16), "v0.9.1  •  MIT  •  Python + PySide6",
              fill=(60, 60, 80), font=_font("regular", 16), anchor="rm")

    img.save(out_path, "PNG")
    print(f"  wrote {out_path.relative_to(ROOT)}")


def make_banner(out_path: Path, w=900, h=180):
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)

    # Gradient left to right
    for x in range(w):
        t = max(0.0, 1 - x / (w * 0.7))
        r2 = int(PURPLE[0] * t * 0.5 + BG[0])
        g2 = int(PURPLE[1] * t * 0.5 + BG[1])
        b2 = int(PURPLE[2] * t * 0.5 + BG[2])
        draw.line([(x, 0), (x, h)], fill=(r2, g2, b2))

    _logo_circle(draw, cx=90, cy=h//2, r=44)

    draw.text((152, h//2 - 22), "PapaRaZ",
              fill=WHITE, font=_font("bold", 52), anchor="lm")
    draw.text((156, h//2 + 28),
              "Screen Capture & Annotation for Windows",
              fill=GREY_M, font=_font("regular", 18), anchor="lm")

    img.save(out_path, "PNG")
    print(f"  wrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    print("Generating images...")
    make_social(ASSETS / "social_preview.png")
    make_banner(ASSETS / "banner.png")
    print("Done.")
