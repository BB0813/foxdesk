"""Convert logo.png to logo.ico for Windows installer."""
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Installing Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image

src = Path("static/logo.png")
dst = Path("static/logo.ico")

if not src.exists():
    print(f"ERROR: {src} not found")
    sys.exit(1)

img = Image.open(src)
# Generate multiple sizes for ICO
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(dst, format="ICO", sizes=sizes)
print(f"Created {dst} ({dst.stat().st_size} bytes)")
