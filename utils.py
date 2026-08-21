import os
import re
import sys
import platform
import subprocess
import datetime
from PIL import Image, ImageFont, ImageOps


def get_system_font(font_name: str = "bold", size: int = 40):
    """
    Load a true-type font with support for macOS, Windows, and Linux.
    Falls back gracefully if fonts are missing.
    """
    candidates = []
    current_os = platform.system()

    if current_os == "Darwin":  # macOS
        if font_name in ("bold", "title"):
            candidates = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/SFPro.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Futura.ttc"
            ]
        elif font_name in ("mono", "mono_bold"):
            candidates = [
                "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
                "/System/Library/Fonts/Supplemental/Courier New.ttf",
                "/System/Library/Fonts/Supplemental/SFMono-Regular.otf",
                "/System/Library/Fonts/Monaco.ttf",
                "/System/Library/Fonts/Supplemental/Andale Mono.ttf"
            ]
        elif font_name == "light":
            candidates = [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc"
            ]
        else:  # regular
            candidates = [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/System/Library/Fonts/SFPro.ttf",
                "/Library/Fonts/Arial.ttf"
            ]
    elif current_os == "Windows":  # Windows
        if font_name in ("bold", "title"):
            candidates = [
                "C:/Windows/Fonts/segoeuib.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/calibrib.ttf",
                "C:/Windows/Fonts/tahomabd.ttf"
            ]
        elif font_name in ("mono", "mono_bold"):
            candidates = [
                "C:/Windows/Fonts/consolab.ttf",
                "C:/Windows/Fonts/consola.ttf",
                "C:/Windows/Fonts/courbd.ttf",
                "C:/Windows/Fonts/cour.ttf",
                "C:/Windows/Fonts/lucon.ttf"
            ]
        elif font_name == "light":
            candidates = [
                "C:/Windows/Fonts/segoeuil.ttf",
                "C:/Windows/Fonts/calibril.ttf",
                "C:/Windows/Fonts/arial.ttf"
            ]
        else:  # regular
            candidates = [
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/tahoma.ttf"
            ]
    else:  # Linux & other
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
        ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    try:
        return ImageFont.load_default()
    except Exception:
        return None


def parse_folder_metadata(folder_path: str):
    """
    Parse date, film stock, and roll info from folder name.
    Supports formats like:
      - isopatrusute_2026-08-20_Kodak-Portra-400
      - isopatrusute_order-50189_2026-08-20_Portra_400
      - 2026-08-20_Kodak_Gold_200
      - MyPhotos_2026-08-20
    """
    if not folder_path:
        return "", "", ""

    folder_name = os.path.basename(os.path.normpath(folder_path))
    date_str = ""
    film_stock = ""

    # Match photoOrganizer format: isopatrusute_(order-..._)?YYYY-MM-DD_Film-Stock
    match = re.match(r'^isopatrusute_(?:order-[^\_]+_)?(\d{4}-\d{2}-\d{2})_(.+)$', folder_name)
    if match:
        date_str = match.group(1)
        film_stock = match.group(2).replace('-', ' ').replace('_', ' ').strip()
    else:
        # Check if date exists anywhere in folder name
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', folder_name)
        if date_match:
            date_str = date_match.group(1)
        else:
            date_str = datetime.date.today().strftime("%Y-%m-%d")

        # Try to infer film stock from remaining folder name
        clean_name = folder_name.replace(date_str, '').replace('isopatrusute', '').replace('_', ' ').replace('-', ' ').strip()
        if clean_name:
            film_stock = clean_name

    roll_title = f"{film_stock.upper()}" if film_stock else "ANALOG ROLL"
    return roll_title, date_str, film_stock


def load_preview_thumbnail(img_path: str, max_dim: int = 500) -> Image.Image:
    """
    Fast loader that creates a downscaled thumbnail in memory using PIL draft mode
    and EXIF orientation for rapid, lag-free live preview rendering.
    """
    try:
        with Image.open(img_path) as img:
            try:
                # Fast DCT downsampling for JPEGs
                img.draft('RGB', (max_dim, max_dim))
            except Exception:
                pass
            img = ImageOps.exif_transpose(img)
            img.thumbnail((max_dim, max_dim), Image.Resampling.BILINEAR)
            if img.mode != "RGB":
                img = img.convert("RGB")
            return img.copy()
    except Exception:
        return None


def calculate_grid_layout(canvas_w: int, canvas_h: int, num_items: int,
                          cols: int = 6, rows_per_sheet: int = 6,
                          show_header: bool = True, show_captions: bool = True,
                          margin_x: int = 350, margin_top: int = 240, margin_bottom: int = 240,
                          header_height: int = 420, spacing_x: int = 90, spacing_y: int = 140,
                          caption_height: int = 120, frame_aspect: float = 1.5):
    """
    Calculates exact bounding box coordinates for each frame on the canvas.
    """
    import math

    items_on_sheet = min(num_items, cols * rows_per_sheet)
    actual_rows = max(1, math.ceil(items_on_sheet / cols)) if items_on_sheet > 0 else 1
    grid_rows = rows_per_sheet if rows_per_sheet > 0 else actual_rows

    avail_w = canvas_w - (2 * margin_x)
    actual_header_h = header_height if show_header else 0
    avail_h = canvas_h - margin_top - margin_bottom - actual_header_h

    # Available space for frames
    total_gap_w = (cols - 1) * spacing_x
    max_frame_w = (avail_w - total_gap_w) / cols if cols > 0 else avail_w

    total_gap_h = (grid_rows - 1) * spacing_y
    actual_caption_h = caption_height if show_captions else 0
    total_caption_h = grid_rows * actual_caption_h
    max_frame_h = (avail_h - total_gap_h - total_caption_h) / grid_rows if grid_rows > 0 else avail_h

    # Fit 3:2 aspect ratio within the cell
    if max_frame_h <= 0 or max_frame_w <= 0:
        frame_w, frame_h = 100, 66
    elif max_frame_w / max_frame_h > frame_aspect:
        frame_h = max_frame_h
        frame_w = frame_h * frame_aspect
    else:
        frame_w = max_frame_w
        frame_h = frame_w / frame_aspect

    frame_w = max(1, int(frame_w))
    frame_h = max(1, int(frame_h))

    # Calculate actual total grid dimensions
    total_grid_w = (cols * frame_w) + total_gap_w
    total_grid_h = (grid_rows * (frame_h + actual_caption_h)) + total_gap_h

    # Center grid within available canvas space
    start_x = int(margin_x + (avail_w - total_grid_w) / 2)
    start_y = int(margin_top + actual_header_h + (avail_h - total_grid_h) / 2)

    boxes = []
    for i in range(items_on_sheet):
        c = i % cols
        r = i // cols
        fx = start_x + c * (frame_w + spacing_x)
        fy = start_y + r * (frame_h + actual_caption_h + spacing_y)
        boxes.append({
            "index": i,
            "col": c,
            "row": r,
            "frame_box": (fx, fy, fx + frame_w, fy + frame_h),
            "caption_box": (fx, fy + frame_h + 8, fx + frame_w, fy + frame_h + actual_caption_h) if show_captions else None,
            "frame_w": frame_w,
            "frame_h": frame_h
        })

    return {
        "boxes": boxes,
        "frame_w": frame_w,
        "frame_h": frame_h,
        "grid_w": total_grid_w,
        "grid_h": total_grid_h,
        "start_x": start_x,
        "start_y": start_y,
        "items_per_sheet": cols * rows_per_sheet,
        "header_y": margin_top,
        "header_h": actual_header_h
    }


def determine_auto_grid(num_photos: int, canvas_w: int, canvas_h: int) -> tuple:
    """
    Automatically determine optimal columns and rows:
    - 36 or less photos: 6 columns x 6 rows (classic 36-frame 35mm contact sheet).
    - 37 or more photos: 5 columns x 8 rows or 8 columns x 5 rows, whichever
      fits the canvas aspect ratio and yields larger frame area.
    """
    if num_photos <= 36:
        return 6, 6

    # Compare 5 cols x 8 rows vs 8 cols x 5 rows
    l_5x8 = calculate_grid_layout(canvas_w, canvas_h, num_photos, cols=5, rows_per_sheet=8)
    l_8x5 = calculate_grid_layout(canvas_w, canvas_h, num_photos, cols=8, rows_per_sheet=5)

    area_5x8 = l_5x8["frame_w"] * l_5x8["frame_h"]
    area_8x5 = l_8x5["frame_w"] * l_8x5["frame_h"]

    if area_8x5 >= area_5x8:
        return 8, 5
    else:
        return 5, 8


def sanitize_filename(name: str) -> str:
    """Strip illegal filesystem characters."""
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()


def reveal_in_file_manager(path: str):
    """Open folder in native OS file manager (Finder / Explorer / Nautilus)."""
    if not os.path.exists(path):
        return False
    
    target_dir = path if os.path.isdir(path) else os.path.dirname(path)
    system_name = platform.system()

    try:
        if system_name == "Darwin":
            subprocess.Popen(["open", target_dir])
        elif system_name == "Windows":
            subprocess.Popen(["explorer", os.path.normpath(target_dir)])
        else:
            subprocess.Popen(["xdg-open", target_dir])
        return True
    except Exception as e:
        print(f"Error revealing in file manager: {e}")
        return False
