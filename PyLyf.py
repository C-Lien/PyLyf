"""
Author : CHRISTOPHER LIEN
Date   : 2025-08-04
"""

################################################################################
## Initial Setup and Configuration
################################################################################

# ────────────────── NATIVE IMPORTS
import sys, csv, random, base64, datetime as dt, ctypes
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from PIL import Image

# ────────────────── EXTERNAL IMPORTS
import pyautogui
from textwrap import dedent

from playwright.sync_api import sync_playwright
from playwright._impl._errors import TargetClosedError
import time, logging

# ────────────────── CONSTANTS
HOME = Path(r"C:\ProgramData\PyLyf")
CONFIG_PATH = HOME / "CONFIG"
STYLE_PATH = HOME / "STYLE.css"
WEEKS_PER_YEAR = 52
SPI_SETWALLPAPER = 20  # SystemParametersInfo flag


# ────────────────── DIRECTORY
def create_directory():
    if HOME.exists():
        return
    root = tk.Tk()
    root.withdraw()
    if not messagebox.askyesno("Create Directory", f"Create {HOME}?"):
        sys.exit()
    (HOME / "Wallpapers").mkdir(parents=True)
    (HOME / "Generated").mkdir()
    root.destroy()


create_directory()

# ────────────────── CONFIG
cfg = {
    k: None
    for k in (
        "WALLPAPER_DIRECTORY",
        "GENERATED_WALLPAPER_PATH",
        "DATES_PATH",
        "FONT_PATH",
        "BIRTH_DATE",
        "TOTAL_YEARS",
        "TICK_FREQUENCY",
    )
}

with (HOME / "CONFIG").open() as f:
    for k, v in (l.strip().split("=", 1) for l in f):
        if k.strip() in cfg:
            cfg[k.strip()] = v.strip().strip('"')

FONT_DEFAULT = "Helvetica"
WALL_DIR = Path(cfg["WALLPAPER_DIRECTORY"])
GEN_PATH = Path(cfg["GENERATED_WALLPAPER_PATH"])
DATES_PATH = Path(cfg["DATES_PATH"])
FONT_PATH = cfg["FONT_PATH"]
BIRTH_DATE = dt.datetime.strptime(cfg["BIRTH_DATE"], "%d/%m/%Y").date()
TOTAL_YEARS = int(cfg["TOTAL_YEARS"])
TICK_FREQUENCY = int(cfg["TICK_FREQUENCY"])
SCREEN_W, SCREEN_H = map(int, pyautogui.size())

# ────────────────── CSS
STYLE = STYLE_PATH.read_text(encoding="utf-8")

################################################################################
## Choose & Prepare Wallpaper
################################################################################


def pick_random_jpg(root: Path) -> Path:
    while True:
        subs = [x for x in root.iterdir() if x.is_dir()]
        jpgs = [x for x in root.iterdir() if x.suffix.lower() == ".jpg"]
        if jpgs:
            return random.choice(jpgs)
        if subs:
            root = random.choice(subs)
        else:
            raise FileNotFoundError("No .jpg files below", root)


def crop_to_screen(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        w_ratio = SCREEN_W / im.width
        h_ratio = SCREEN_H / im.height
        scale = max(w_ratio, h_ratio)
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        left = (im.width - SCREEN_W) // 2
        top = (im.height - SCREEN_H) // 2
        im = im.crop((left, top, left + SCREEN_W, top + SCREEN_H))
        im.save(dst, format="PNG")


wall_src = pick_random_jpg(Path(WALL_DIR))
wall_png = Path(WALL_DIR) / "wallpaper_base.png"
crop_to_screen(wall_src, wall_png)

################################################################################
## Build HTML
################################################################################


def make_font_face() -> str:
    if not FONT_PATH or not Path(FONT_PATH).is_file():
        print(f"Using default font: {FONT_DEFAULT}")
        return ""
    uri = Path(FONT_PATH).as_uri()
    print(f"Using custom font: {uri}")
    return f"""
    @font-face {{
        font-family:'custom';
        src:url('{uri}');
    }}"""


def build_ticks_html() -> tuple[str, float]:
    weeks_total = TOTAL_YEARS * WEEKS_PER_YEAR
    lived_weeks = (dt.date.today() - BIRTH_DATE).days // 7
    lived_pct = lived_weeks / weeks_total * 100

    ticks = []
    for yr in range(0, TOTAL_YEARS + 1, TICK_FREQUENCY):
        x = yr / TOTAL_YEARS * 100
        ticks.append(
            f'<div class="tick year" style="--x:{x}%;" data-label="{yr}"></div>'
        )

    with open(DATES_PATH, newline="") as fh:  # DATES CSV Tick Data
        rd = csv.reader(fh)
        for d, label, scale in rd:
            ev = dt.datetime.strptime(d, "%d/%m/%Y").date()
            pct = ((ev - BIRTH_DATE).days / 7) / weeks_total * 100
            ticks.append(
                f'<div class="tick ev" style="--x:{pct}%;--scale:{scale};" '
                f'data-label="{label}"></div>'
            )
    return "".join(ticks), lived_pct


def build_html(bg_png: Path) -> str:
    wall_uri = "data:image/png;base64," + base64.b64encode(bg_png.read_bytes()).decode(
        "ascii"
    )

    ticks_html, lived_pct = build_ticks_html()
    font_css = make_font_face()
    bar_height = min(SCREEN_H / 52, 10)

    return dedent(
        f"""\
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
          {font_css}
          {STYLE}

          body{{
              background:url('{wall_uri}') center/cover no-repeat fixed;
              font:12px {'custom' if font_css else FONT_DEFAULT};
          }}

          .bar-wrap{{height:{bar_height:.2f}px}}
          </style>
        </head>
        <body>
          <div class="bar-wrap">
            <div class="lived" style="width:{lived_pct:.4f}%"></div>
            {ticks_html}
          </div>
        </body>
        </html>
        """
    )


html_doc = build_html(wall_png)

################################################################################
## Render via PlayWright
################################################################################
generated_wallpaper = Path(GEN_PATH) / "wallpaper.png"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        channel="msedge",  # MS Edge Only - Assumption W11 only machines
        args=["--force-device-scale-factor=1"],
    )
    page = browser.new_page(
        viewport={"width": SCREEN_W, "height": SCREEN_H}, device_scale_factor=1
    )
    page.set_content(html_doc, wait_until="networkidle")
    page.screenshot(path=str(generated_wallpaper))
    browser.close()

print(f"Wallpaper rendered: {generated_wallpaper}")

################################################################################
## Set Image as Background
################################################################################
if ctypes.windll.user32.SystemParametersInfoW(
    SPI_SETWALLPAPER, 0, str(generated_wallpaper), 3
):
    print("Wallpaper Update - Success")
else:
    print("Wallpaper Update - Failure")
