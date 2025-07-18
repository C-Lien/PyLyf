'''
Author:     CHRISTOPHER LIEN
DATE:       20250420
VERSION:    1.1
'''
import os
import sys
import csv
import random
import datetime
import shutil
import ctypes
import pyautogui
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import base64
from html import escape
from html2image import Html2Image   # pip install html2image
from pathlib import Path

################################################################################
## Configuration Variables
################################################################################

# CONSTANT DIRECTORIES WHERE:
# THE CSV FOR TIMELINE DATA MUST CONTAIN NO HEADERS. EXAMPLE:
#
# 05/06/23,Example Event,1
# 07/12/22,Christmas Event,2
# 02/04/89,Grandmas Birthday,1
#
# NOTE THE DATE IS UNORDERED AND IN THE FORM %d%m%y
# NOTE COLUMN 3 CONTROLS TICK MULTIPLES BY MULTIPLICATION - x3 VALUES ARE RECOMMENDED
# i.e. 1 = 5px, 3 = 15px, 5 = 25px etc. Experiment for best outcome for your setup.
#
# FONT_PATH - THE LOCATION OF THE SELECTED FONT. REPLACE WITH YOUR OWN SELECTED CHOICE
# OTHERWISE DEFAULT WILL BE USED (WHICH IS UGLY). WINDOWS 11 FONT DATA ARE LOCATED IN:
# C:\Users\%USER%\AppData\Local\Microsoft\Windows\Fonts\

################################################################################
## Generate home directory and data
################################################################################

HOME_DIRECTORY = r"C:\ProgramData\PyLyf"


def find_edge_exec() -> str:
    """
    Return absolute path to msedge.exe (Chromium-based Edge).
    Raises FileNotFoundError if nothing sensible is found.
    """

    candidates = [
        Path(os.getenv("PROGRAMFILES",  r"C:/Program Files"))       / "Microsoft/Edge/Application/msedge.exe",
        Path(os.getenv("PROGRAMFILES(X86)", r"C:/Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]

    # 1️ check the hard-coded locations
    for p in candidates:
        if p.is_file():
            return str(p)

    # 2️ fall back to whatever is on PATH (rare on Windows, but harmless)
    msedge = shutil.which("msedge")
    if msedge:
        return msedge

    raise FileNotFoundError(
        "Could not locate Microsoft Edge (msedge.exe). "
        "Please install Edge or point html2image at a Chromium-based browser."
    )

def create_directory():
    if not os.path.exists(HOME_DIRECTORY):
        root = tk.Tk()
        root.withdraw()

        result = messagebox.askyesno("Create Directory",
                                     f"The directory {HOME_DIRECTORY} does not exist. Would you like to create it?")

        if result:
            try:
                os.makedirs(HOME_DIRECTORY)
                os.makedirs(os.path.join(HOME_DIRECTORY, "Wallpapers"))
                os.makedirs(os.path.join(HOME_DIRECTORY, "Generated"))

                def resource_path(data):
                    path = os.path.dirname(os.path.abspath(__file__))
                    base_path = getattr(sys, '_MEIPASS', path)

                    return os.path.join(base_path, data)

                images = ["example_1.jpg", "example_2.jpg", "example_3.jpg", "example_4.jpg"]

                for image in images:
                    image_directory = resource_path(image)
                    destination = os.path.join(os.path.join(HOME_DIRECTORY, "Wallpapers"), image)
                    shutil.move(image_directory, destination)
                    print(f"Moved {image} to {destination}")

                config = resource_path("CONFIG")
                config_destination = os.path.join(HOME_DIRECTORY, "CONFIG")
                shutil.move(config, config_destination)
                print(f"Moved CONFIG to {config_destination}")

                dates = resource_path("DATES.csv")
                dates_destination = os.path.join(HOME_DIRECTORY, "DATES.csv")
                shutil.move(dates, dates_destination)
                print(f"Moved DATES.csv to {dates_destination}")

                messagebox.showinfo("Success", f"Directory created at {HOME_DIRECTORY}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create directory: {e}")
        else:
            messagebox.showinfo("Cancelled", "Directory creation cancelled.")

        root.destroy()

create_directory()

################################################################################
## Extract CONFIG data for processing
################################################################################

CONFIG_PATH = os.path.join(HOME_DIRECTORY,"CONFIG")

# POPULATE FROM CONFIG FILE
WALLPAPER_DIRECTORY = None
GENERATED_WALLPAPER_PATH = None
DATES_PATH = None
FONT_PATH = None
BIRTH_DATE = None
TOTAL_YEARS = None

required_keys = {
    "WALLPAPER_DIRECTORY": None,
    "GENERATED_WALLPAPER_PATH": None,
    "DATES_PATH": None,
    "FONT_PATH": None,
    "BIRTH_DATE": None,
    "TOTAL_YEARS": None
}

try:
    with open(CONFIG_PATH, 'r') as file:
        reader = csv.reader(file, delimiter='=')

        for line in reader:
            if len(line) != 2:
                raise ValueError("CONFIG format not compliant")

            key, value = line
            key = key.strip()
            value = value.strip().strip('"')

            if key in required_keys:
                required_keys[key] = value

        if None in required_keys.values():
            raise ValueError("CONFIG format not compliant")

        WALLPAPER_DIRECTORY = required_keys["WALLPAPER_DIRECTORY"]
        GENERATED_WALLPAPER_PATH = required_keys["GENERATED_WALLPAPER_PATH"]
        DATES_PATH = required_keys["DATES_PATH"]
        FONT_PATH = required_keys["FONT_PATH"]
        BIRTH_DATE = datetime.datetime.strptime(required_keys["BIRTH_DATE"], '%d/%m/%Y').date()
        TOTAL_YEARS = int(required_keys["TOTAL_YEARS"])

    print("Configurations Loaded Successfully!")

except FileNotFoundError:
    print(f"Couldn't find the config file at {CONFIG_PATH}.")
except ValueError as e:
    print(e)

# CONSTANT VARIABLES
DEFAULT_FONT_SIZE = 12
WEEKS_PER_YEAR = 52
SPI_SETDESKWALLPAPER = 20

screen_width, screen_height = pyautogui.size()

################################################################################
## Getting Image
################################################################################

def choose_random_wallpaper(WALLPAPER_DIRECTORY):
    current_directory = WALLPAPER_DIRECTORY
    while True:
        entries = os.listdir(current_directory)
        sub_dirs = [entry for entry in entries if os.path.isdir(os.path.join(current_directory, entry))]
        jpg_files = [entry for entry in entries if entry.lower().endswith('.jpg')]

        if jpg_files:
            selected_file = random.choice(jpg_files)
            return os.path.join(current_directory, selected_file)
        elif sub_dirs:
            current_directory = os.path.join(current_directory, random.choice(sub_dirs))
        else:
            break

################################################################################
## Sizing Image
################################################################################

def resize_and_crop_image_to_screen(image_path, screen_width, screen_height, save_path):
    with Image.open(image_path) as img:
        img_width, img_height = img.size

        if img_width < screen_width or img_height < screen_height:
            print("Wallpaper " + image_path + " rejected.")
            return None

        width_ratio = screen_width / img_width
        height_ratio = screen_height / img_height
        resize_ratio = max(width_ratio, height_ratio)

        new_width = int(img_width * resize_ratio)
        new_height = int(img_height * resize_ratio)
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)

        left = (new_width - screen_width) / 2
        top = (new_height - screen_height) / 2
        right = (new_width + screen_width) / 2
        bottom = (new_height + screen_height) / 2

        cropped_img = resized_img.crop((left, top, right, bottom))
        img_rgba = cropped_img.convert('RGBA')

        img_rgba.putdata([(r, g, b, a) for r, g, b, a in img_rgba.getdata()])

        img_rgba.save(save_path, "PNG")
        return save_path

while True:
    selected_wallpaper_path = choose_random_wallpaper(WALLPAPER_DIRECTORY)
    save_path = os.path.join(GENERATED_WALLPAPER_PATH, "wallpaper.png")
    resized_wallpaper = resize_and_crop_image_to_screen(selected_wallpaper_path, screen_width, screen_height, save_path)

    if resized_wallpaper:
        print("Wallpaper " + selected_wallpaper_path + " selected.")
        break
    else:
        selected_wallpaper_path = choose_random_wallpaper(WALLPAPER_DIRECTORY)

################################################################################
## Adding Image Details and Anxiety
################################################################################
'''
def create_lifespan_bar(image_path, birth_date, screen_width, screen_height):
    today = datetime.date.today()
    weeks_lived = (today - birth_date).days // 7
    bar_length = screen_width * 0.9
    square_height = min(screen_height / WEEKS_PER_YEAR, 10)
    tick_height = square_height / 1.5
    x_offset = (screen_width - bar_length) / 2
    y_offset = screen_height / 1.1 - square_height / 2 # /2 = centre, /20 = top, 1.1 = bottom
    fill_colour = "white"
    outline_colour = "black"
    outline_width = 1.0

    bg_x_margin = tick_height * 5
    bg_y_margin = square_height + tick_height + 30 # The '30' should be dynamic to the largest tick received * 10

    def modify_wallpaper_section(image_path, x_offset, y_offset, bar_length, square_height, tick_height, screen_width, screen_height):
        with Image.open(image_path).convert("RGBA") as base_image:
            base_image = base_image.resize((screen_width, screen_height), Image.LANCZOS)
            area = (
                int(x_offset),
                int(y_offset),
                int(bar_length),
                int(square_height)
            )
            cropped_section = base_image.crop(area)

            sharpness = ImageEnhance.Sharpness(cropped_section)
            cropped_section = sharpness.enhance(0)

            base_image.paste(cropped_section, area)
            base_image.save(image_path)

    modify_wallpaper_section(
        image_path=image_path,
        x_offset=x_offset - bg_x_margin,
        y_offset=y_offset - bg_y_margin,
        bar_length=x_offset + bar_length + bg_x_margin,
        square_height=y_offset + square_height + bg_y_margin,
        tick_height=tick_height,
        screen_width=screen_width,
        screen_height=screen_height
    )

    def add_date_annotations(draw, font, x_offset, y_offset, bar_length, birth_date, tick_height, fill_colour, outline_width, outline_colour):
        with open(DATES_PATH, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                event_date_str, event_text, tick_scale_str = row
                event_date = datetime.datetime.strptime(event_date_str, '%d/%m/%Y').date()

                weeks_since_birth = (event_date - birth_date).days / 7
                tick_x = x_offset + (weeks_since_birth / (TOTAL_YEARS * WEEKS_PER_YEAR)) * bar_length

                current_tick_height = tick_height * int(tick_scale_str) # tick_height * value (col[3]) where * 3 recommended
                draw.line([tick_x, y_offset, tick_x, y_offset - current_tick_height], fill=outline_colour)

                horizontal_line_length = 3
                horizontal_line_start = (tick_x, y_offset - current_tick_height)
                horizontal_line_end = (tick_x + horizontal_line_length, y_offset - current_tick_height)
                draw.line([horizontal_line_start, horizontal_line_end], fill=outline_colour)

                y_pos = y_offset - square_height - current_tick_height + 3
                text_position = (tick_x + 5, y_pos)
                draw.text(text_position, event_text, fill=fill_colour, font=font, stroke_width=outline_width, stroke_fill=outline_colour)

    with Image.open(image_path).convert("RGBA") as base_image:
        base_image = base_image.resize((screen_width, screen_height), Image.LANCZOS)
        draw = ImageDraw.Draw(base_image, "RGBA")

        lived_weeks_length = (weeks_lived / (TOTAL_YEARS * WEEKS_PER_YEAR)) * bar_length
        draw.rectangle([x_offset, y_offset, x_offset + lived_weeks_length, y_offset + square_height], fill=fill_colour, outline=outline_colour)
        draw.rectangle([x_offset + lived_weeks_length, y_offset, x_offset + bar_length, y_offset + square_height], outline=outline_colour)
        draw.line([x_offset + lived_weeks_length, y_offset, x_offset + lived_weeks_length, y_offset + square_height], fill=outline_colour)

        try:
            font = ImageFont.truetype(FONT_PATH, DEFAULT_FONT_SIZE)
        except IOError:
            font = ImageFont.load_default()
            print("failed to load custom font. Resorting to default.")

        for year in range(0, TOTAL_YEARS + 1, 5):
            tick_x = x_offset + (year / TOTAL_YEARS) * bar_length
            draw.line([tick_x, y_offset + square_height, tick_x, y_offset + square_height + tick_height], fill=outline_colour)
            text_bbox = draw.textbbox((0, 0), str(year), font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_position = (tick_x - text_width / 2, y_offset + square_height + tick_height)
            draw.text(text_position, str(year), fill=fill_colour, font=font, stroke_width=outline_width, stroke_fill=outline_colour)

        add_date_annotations(draw, font, x_offset, y_offset, bar_length, birth_date, tick_height, fill_colour, outline_width, outline_colour)

        generated_wallpaper = os.path.join(GENERATED_WALLPAPER_PATH, "wallpaper.png")
        base_image.save(generated_wallpaper)

        return generated_wallpaper
    '''
    # -------------------------------------------------
# 1. CREATE HTML (all the drawing happens in CSS)
# -------------------------------------------------
def create_html_wallpaper(
        wallpaper_path: str,
        events_csv: str,
        birth_date: datetime.date,
        total_years: int,
        screen_w: int,
        screen_h: int,
        font_path: str
    ) -> str:
    """
    Returns a single self-contained HTML string with:
      • the wallpaper as a base64 background
      • a life bar at the bottom
      • ticks for every 5th year and every custom event
    """

    # --- embed wallpaper as base64 data URI ------------------------------
    with open(wallpaper_path, "rb") as f:
        b64_wall = base64.b64encode(f.read()).decode("ascii")
    wall_uri = f"data:image/jpeg;base64,{b64_wall}"

    # --- calculate time data --------------------------------------------
    today              = datetime.date.today()
    weeks_lived        = (today - birth_date).days // 7
    weeks_total        = total_years * 52
    lived_pct          = weeks_lived / weeks_total * 100

    # --- build <div> ticks ----------------------------------------------
    tick_elems = []

    #   a) year ticks every 5 years
    for yr in range(0, total_years + 1, 5):
        pct = yr / total_years * 100
        tick_elems.append(
            f'<div class="tick year" style="--x:{pct}%;" data-label="{yr}"></div>'
        )

    #   b) event ticks from CSV
    with open(events_csv) as f:
        rdr = csv.reader(f)
        for date_str, label, scale in rdr:
            ev_date = datetime.datetime.strptime(date_str, "%d/%m/%Y").date()
            pct     = ( (ev_date - birth_date).days / 7 ) / weeks_total * 100
            height  = float(scale)            # 1, 2, 3 … from your CSV
            tick_elems.append(
                f'<div class="tick ev" style="--x:{pct}%; --scale:{height};"'
                f' data-label="{escape(label)}"></div>'
            )

    ticks_html = "\n        ".join(tick_elems)

    # --- optional custom font -------------------------------------------
    font_face_css = ""
    if font_path and os.path.isfile(font_path):
        font_url = Path(font_path).as_uri()
        font_face_css = f"""
        @font-face {{
            font-family: "custom";
            src: url('{font_url}');
        }}"""

    # --- full HTML -------------------------------------------------------
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <style>
        {font_face_css}
        * {{ box-sizing:border-box; margin:0; padding:0; }}
        html,body {{
            width:{screen_w}px; height:{screen_h}px; overflow:hidden;
        }}
        body {{
            background:url('{wall_uri}') center/cover no-repeat fixed;
            font:12px {"custom" if font_face_css else "sans-serif"};
        }}

        /* --- life-bar container ----------------------------------------- */
        .bar-wrap {{
            position:absolute;
            left:5%;               /* 90 % wide */
            width:90%;
            height:10px;           /* will be overwritten below */
            bottom:8%;             /* ~ just above task-bar */
            background:rgba(0,0,0,.45);
            backdrop-filter:blur(6px) brightness(.6);
            border:1px solid rgba(255,255,255,.6);
            border-radius:4px;
        }}
        .lived {{
            position:absolute; top:0; left:0; height:100%;
            width:{lived_pct:.4f}%;
            background:#fff;
        }}

        /* --- ticks ------------------------------------------------------- */
        .tick {{
            position:absolute; bottom:calc(100% + 2px);
            width:1px; background:#000;
            height:calc(var(--scale,1) * 8px);   /* event scale */
            left:var(--x);
            transform:translateX(-.5px);
        }}
        .tick.year {{
            --scale:1;
            background:#fff;
            bottom:-2px;           /* inside bar for year ticks */
            height:6px;
        }}

        /* --- tick labels -------------------------------------------------- */
        .tick::after {{
            content:attr(data-label);
            position:absolute; left:3px; top:-1.25em;
            white-space:nowrap;
            font-size:12px; color:#fff;
            -webkit-text-stroke:1px #000;
        }}
        .tick.year::after {{
            top:1.5em;             /* label below the bar for years */
        }}

    </style>
    </head>
    <body>
        <div class="bar-wrap" style="height:{min(screen_h/52, 10):.2f}px">
            <div class="lived"></div>
        </div>

        {ticks_html}

    </body>
    </html>
    '''
    return html


# -------------------------------------------------
# 2. RENDER HTML -> PNG
# -------------------------------------------------
'''
def html_to_png(html_str: str, out_path: str, screen_w: int, screen_h: int):

    hti = Html2Image(output_path=os.path.dirname(out_path), size=(screen_w, screen_h))
    # html2image can take raw HTML directly:
    hti.screenshot(html_str=html_str, save_as=os.path.basename(out_path))
'''

def html_to_png(html_str: str, out_path: str, screen_w: int, screen_h: int):
    """ Uses html2image (Chromium headless) to screenshot the given HTML.
    """
    edge_exe = find_edge_exec()
    hti = Html2Image(
        browser_executable=edge_exe,
        output_path=os.path.dirname(out_path),
        size=(screen_w, screen_h)
    )
    hti.screenshot(html_str=html_str, save_as=os.path.basename(out_path))


# -------------------------------------------------
# 3. EXPORTED ENTRY POINT (drop-in replacement for
#    your Pillow-based create_lifespan_bar)
# -------------------------------------------------
def create_lifespan_bar_html(
        image_path: str,
        birth_date: datetime.date,
        screen_w: int,
        screen_h: int
):
    """ Builds HTML, renders PNG, returns file-system path of that PNG.
    """

    # 3a. Build HTML
    html = create_html_wallpaper(
        wallpaper_path=image_path,
        events_csv=DATES_PATH,
        birth_date=birth_date,
        total_years=TOTAL_YEARS,
        screen_w=screen_w,
        screen_h=screen_h,
        font_path=FONT_PATH
    )

    # 3b. Screenshot
    out_png = os.path.join(GENERATED_WALLPAPER_PATH, "wallpaper.png")
    html_to_png(html, out_png, screen_w, screen_h)
    return out_png

working_wallpaper = os.path.join(GENERATED_WALLPAPER_PATH, "wallpaper.png")
#generated_wallpaper = create_lifespan_bar(working_wallpaper, BIRTH_DATE, screen_width, screen_height)
generated_wallpaper = create_lifespan_bar_html(working_wallpaper, BIRTH_DATE, screen_width, screen_height)

################################################################################
## Setting Image as Background
################################################################################

def set_wallpaper(generated_wallpaper):
    success = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, generated_wallpaper, 3)
    return success

if set_wallpaper(generated_wallpaper):
    print("Wallpaper successfully changed.")
else:
    print("Failed to change wallpaper.")
