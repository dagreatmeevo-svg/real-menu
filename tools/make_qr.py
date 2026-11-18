"""Make one QR code PNG per dish in dishes.json.

Usage:
    pip install "qrcode[pil]"
    python tools/make_qr.py https://yourname.github.io/real-menu/
    python tools/make_qr.py https://yourname.github.io/real-menu/ --out qr --size 1200

Each QR opens <base>?dish=<id>. Files are written to qr/<id>.png with the
dish's English name printed under the code.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlencode, urlsplit

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_Q
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('Missing libraries. Run:  pip install "qrcode[pil]"')

ROOT = Path(__file__).resolve().parent.parent


def dish_url(base: str, dish_id: str) -> str:
    sep = "&" if "?" in base else "?"
    return base + sep + urlencode({"dish": dish_id})


def make_png(url: str, caption: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, border=4, box_size=10)
    qr.add_data(url)
    qr.make(fit=True)
    code = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    code = code.resize((size, size), Image.NEAREST)

    pad = size // 8
    canvas = Image.new("RGB", (size, size + pad), "white")
    canvas.paste(code, (0, 0))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", pad // 2)
    except OSError:
        font = ImageFont.load_default(size=pad // 2)
    w = draw.textlength(caption, font=font)
    draw.text(((size - w) / 2, size - pad // 6), caption, fill="black", font=font)
    return canvas


def main() -> None:
    ap = argparse.ArgumentParser(description="One QR PNG per dish in dishes.json")
    ap.add_argument("base_url", help="HTTPS address of the viewer, e.g. https://yourname.github.io/real-menu/")
    ap.add_argument("--menu", default=str(ROOT / "dishes.json"), help="path to dishes.json")
    ap.add_argument("--out", default=str(ROOT / "qr"), help="output folder")
    ap.add_argument("--size", type=int, default=1000, help="QR width in pixels (1000 ≈ 8.5 cm at 300 dpi)")
    args = ap.parse_args()

    parts = urlsplit(args.base_url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        sys.exit("base_url must start with https://")
    if parts.scheme != "https":
        print("warning: camera and AR only work on https:// addresses", file=sys.stderr)

    dishes = json.loads(Path(args.menu).read_text(encoding="utf-8")).get("dishes", [])
    if not dishes:
        sys.exit("No dishes found in " + args.menu)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for d in dishes:
        url = dish_url(args.base_url, d["id"])
        caption = (d.get("name") or {}).get("en") or d["id"]
        path = out / f"{d['id']}.png"
        make_png(url, caption, args.size).save(path)
        print(f"{path}  ->  {url}")


if __name__ == "__main__":
    main()
