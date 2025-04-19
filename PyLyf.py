'''
This was a rushed proof-of-concept. Ample room for improvement everywhere.

Author:     CHRISTOPHER LIEN
DATE:       20250420
VERSION:    1.0
'''

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
import pyautogui
import datetime
import ctypes
import os
import random
import csv

################################################################################
## Configuration Variables
################################################################################

# CONSTANT DIRECTORIES WHERE:
# WALLPAPER_DIRECTORY - THE START POINT FOR WALLPAPERS TO CHOOSE FROM, THE PROGRAM
# WILL TRAWL THROUGH THIS FOLDER AND PICK ONE AT RANDOM THAT FITS THE MAIN MONITOR.
# GENERATED_WALLPAPER_PATH - THE SAVE LOCATION FOR THE WORKING WALLPAPER
# CSV_PATH - THE CSV LOCATION FOR TIMELINE DATA WITH NO HEADERS. EXAMPLE:
#
# 05/06/23,Example Event,1
# 07/12/22,Christmas Event,2
# 02/04/89,Grandmas Birthday,1
#
# NOTE THE DATE IS UNORDERED AND IN THE FORM %d%m%y
# NOTE COLUMN 3 is controls whether data are 'tall' (2) or 'short' (1)
#   Generate a wallpaper with 1 and 2 values and you will understand what this does.
#
# FONT_PATH - THE LOCATION OF THE SELECTED FONT. REPLACE WITH YOUR OWN SELECTED CHOICE
# OTHERWISE DEFAULT WILL BE USED (WHICH IS UGLY). WINDOWS 11 FONT DATA ARE LOCATED IN:
# C:\Users\%USER%\AppData\Local\Microsoft\Windows\Fonts\

WALLPAPER_DIRECTORY = r"YOUR_WALLPAPER_DIRECTORY"
GENERATED_WALLPAPER_PATH = r"YOUR_SAVE_DIRECTORY"
CSV_PATH = r"YOUR_CSV_DIRECTORY"
FONT_PATH = r"YOUR_FONT_DIRECTORY"

# CONSTANT VARIABLES
DEFAULT_FONT_SIZE = 12
TOTAL_YEARS = 80                        # TARGET MAX YEAR
WEEKS_PER_YEAR = 52
BIRTH_DATE = datetime.date(1900, 1, 1)  # USER BIRTHDAY IN FORM (YYYY,MM,DD)
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
    resized_wallpaper = resize_and_crop_image_to_screen(selected_wallpaper_path, screen_width, screen_height, GENERATED_WALLPAPER_PATH)

    if resized_wallpaper:
        print("Wallpaper " + selected_wallpaper_path + " selected.")
        break
    else:
        selected_wallpaper_path = choose_random_wallpaper(WALLPAPER_DIRECTORY)

################################################################################
## Adding Image Details and Anxiety
################################################################################

def create_lifespan_bar(image_path, birth_date, screen_width, screen_height):
    today = datetime.date.today()
    weeks_lived = (today - birth_date).days // 7
    bar_length = screen_width * 0.9
    square_height = min(screen_height / WEEKS_PER_YEAR, 10)
    tick_height = square_height / 1.5
    x_offset = (screen_width - bar_length) / 2
    y_offset = screen_height / 1.1 - square_height / 2 # /2 = centre, /20 = top, 1.1 = bottom
    bg_x_margin = tick_height * 4
    bg_y_margin = square_height + tick_height + 10

    def convert_section_to_black_and_white(image_path, x_offset, y_offset, bar_length, square_height, tick_height, screen_width, screen_height):
        with Image.open(image_path).convert("RGBA") as base_image:
            base_image = base_image.resize((screen_width, screen_height), Image.LANCZOS)
            area = (
                int(x_offset),
                int(y_offset),
                int(bar_length),
                int(square_height)
            )

            cropped_section = base_image.crop(area)
            bw_section = ImageOps.grayscale(cropped_section)
            bw_section = bw_section.convert("RGBA")

            sharpness = ImageEnhance.Sharpness(bw_section)
            bw_section = sharpness.enhance(0) # Makin it blurry

            base_image.paste(bw_section, area)
            base_image.save(image_path)

    convert_section_to_black_and_white(
        image_path=image_path,
        x_offset=x_offset - bg_x_margin,
        y_offset=y_offset - bg_y_margin,
        bar_length=x_offset + bar_length + bg_x_margin,
        square_height=y_offset + square_height + bg_y_margin,
        tick_height=tick_height,
        screen_width=screen_width,
        screen_height=screen_height
    )

    def add_date_annotations(draw, font, x_offset, y_offset, bar_length, birth_date, tick_height):
        with open(CSV_PATH, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                event_date_str, event_text, tick_scale_str = row
                event_date = datetime.datetime.strptime(event_date_str, '%d/%m/%y').date()

                weeks_since_birth = (event_date - birth_date).days / 7
                tick_x = x_offset + (weeks_since_birth / (TOTAL_YEARS * WEEKS_PER_YEAR)) * bar_length

                current_tick_height = tick_height if tick_scale_str.strip() == '1' else tick_height * 3
                draw.line([tick_x, y_offset, tick_x, y_offset - current_tick_height], fill="black")

                horizontal_line_length = 3
                horizontal_line_start = (tick_x, y_offset - current_tick_height)
                horizontal_line_end = (tick_x + horizontal_line_length, y_offset - current_tick_height)
                draw.line([horizontal_line_start, horizontal_line_end], fill="black")

                text_position = (tick_x + 5, y_offset - square_height - current_tick_height + 3)
                draw.text(text_position, event_text, fill="black", font=font)

    with Image.open(image_path).convert("RGBA") as base_image:
        base_image = base_image.resize((screen_width, screen_height), Image.LANCZOS)
        draw = ImageDraw.Draw(base_image, "RGBA")

        lived_weeks_length = (weeks_lived / (TOTAL_YEARS * WEEKS_PER_YEAR)) * bar_length
        draw.rectangle([x_offset, y_offset, x_offset + lived_weeks_length, y_offset + square_height], fill=(26, 34, 35, 255), outline="black")
        draw.rectangle([x_offset + lived_weeks_length, y_offset, x_offset + bar_length, y_offset + square_height], outline="black")
        draw.line([x_offset + lived_weeks_length, y_offset, x_offset + lived_weeks_length, y_offset + square_height], fill="black")

        try:
            font = ImageFont.truetype(FONT_PATH, DEFAULT_FONT_SIZE)
        except IOError:
            font = ImageFont.load_default()
            print("failed to load custom font. Resorting to default.")

        for year in range(0, TOTAL_YEARS + 1, 5):
            tick_x = x_offset + (year / TOTAL_YEARS) * bar_length
            draw.line([tick_x, y_offset + square_height, tick_x, y_offset + square_height + tick_height], fill="black")
            text_bbox = draw.textbbox((0, 0), str(year), font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_position = (tick_x - text_width / 2, y_offset + square_height + tick_height)
            draw.text(text_position, str(year), fill="black", font=font)

        add_date_annotations(draw, font, x_offset, y_offset, bar_length, birth_date, tick_height)

        base_image.save(GENERATED_WALLPAPER_PATH)
        return

edited_wallpaper_path = create_lifespan_bar(GENERATED_WALLPAPER_PATH, BIRTH_DATE, screen_width, screen_height)

################################################################################
## Setting Image as Background
################################################################################

def set_wallpaper(GENERATED_WALLPAPER_PATH):
    success = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, GENERATED_WALLPAPER_PATH, 3)
    return success

if set_wallpaper(GENERATED_WALLPAPER_PATH):
    print("Wallpaper successfully changed.")
else:
    print("Failed to change wallpaper.")
