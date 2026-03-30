"""Generate assets/paparaz.ico — multi-resolution icon for PapaRaZ.

Produces a rounded-rectangle "Pz" icon matching the app's purple accent theme.
Run from the project root: python scripts/make_icon.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def _make_frame(size: int) -> Image.Image:
    scale = 4  # supersample for anti-aliasing
    s = size * scale

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: dark purple rounded rectangle
    r = s // 5          # corner radius
    bg = (30, 0, 50, 255)
    accent = (116, 0, 150, 255)

    # Filled rounded rect (background)
    draw.rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=bg)

    # Accent border
    bw = max(2, s // 24)
    draw.rounded_rectangle([bw // 2, bw // 2, s - bw // 2 - 1, s - bw // 2 - 1],
                            radius=r, outline=accent, width=bw)

    # "Pz" text
    font_size = int(s * 0.46)
    font = None
    for fname in ["arialbd.ttf", "Arial Bold.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            font = ImageFont.truetype(fname, font_size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()

    text = "Pz"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (s - tw) // 2 - bbox[0]
    ty = (s - th) // 2 - bbox[1] - int(s * 0.02)

    # Shadow
    draw.text((tx + bw, ty + bw), text, font=font, fill=(0, 0, 0, 160))
    # Main text (white)
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))

    # Downsample with LANCZOS for clean anti-aliasing
    return img.resize((size, size), Image.LANCZOS)


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [_make_frame(s) for s in sizes]

    out = Path("assets/paparaz.ico")
    frames[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"Created {out}  ({', '.join(str(s) for s in sizes)} px)")


if __name__ == "__main__":
    main()
