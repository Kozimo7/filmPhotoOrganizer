import os
import math
from PIL import Image, ImageDraw, ImageOps

from config import (
    DEFAULT_CANVAS_WIDTH,
    DEFAULT_CANVAS_HEIGHT,
    DEFAULT_COLUMNS,
    DEFAULT_ROWS_PER_SHEET,
    DEFAULT_FRAME_ASPECT,
    DEFAULT_ROTATE_PORTRAIT,
    THEMES
)
from utils import get_system_font, load_preview_thumbnail, calculate_grid_layout


class ContactSheetGenerator:
    """
    Core engine for assembling contact sheets from image files.
    Calculates pixel-perfect layouts, resizes images, and draws headers/labels.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

    def render_sheet(self, image_paths: list, page_index: int = 0, total_pages: int = 1,
                     progress_callback=None, is_preview: bool = False, preview_scale: float = 0.12,
                     thumbnail_cache: dict = None) -> Image.Image:
        """
        Renders a single page of the contact sheet.
        If is_preview is True: uses fast memory-cached downscaled thumbnails for rapid web display.
        If is_preview is False: loads original full-resolution master files with Lanczos resampling.
        """
        canvas_w = int(self.config.get("canvas_width", DEFAULT_CANVAS_WIDTH))
        canvas_h = int(self.config.get("canvas_height", DEFAULT_CANVAS_HEIGHT))
        cols = int(self.config.get("columns", DEFAULT_COLUMNS))
        rows_per_sheet = int(self.config.get("rows_per_sheet", DEFAULT_ROWS_PER_SHEET))
        theme_key = self.config.get("theme", "dark")
        theme = THEMES.get(theme_key, THEMES["dark"])

        show_header = self.config.get("show_header", True)
        show_captions = self.config.get("show_captions", True)
        show_border = self.config.get("show_frame_border", True)
        rotate_portrait = self.config.get("rotate_portrait", DEFAULT_ROTATE_PORTRAIT)
        numbering_style = self.config.get("numbering_style", "rebate")

        roll_title = self.config.get("roll_title", "ANALOG ROLL").strip()
        date_str = self.config.get("date_str", "").strip()
        film_stock = self.config.get("film_stock", "").strip()
        camera_info = self.config.get("camera_info", "").strip()
        notes = self.config.get("notes", "").strip()

        # Layout parameters (scaled for canvas resolution)
        scale_factor = canvas_w / 11500.0
        margin_x = int(350 * scale_factor)
        margin_top = int(240 * scale_factor)
        margin_bottom = int(240 * scale_factor)
        header_height = int(420 * scale_factor)
        spacing_x = int(90 * scale_factor)
        spacing_y = int(140 * scale_factor)
        caption_height = int(120 * scale_factor)

        # Scale down dimensions if generating a fast preview
        render_w = int(canvas_w * preview_scale) if is_preview else canvas_w
        render_h = int(canvas_h * preview_scale) if is_preview else canvas_h
        r_scale = preview_scale if is_preview else 1.0

        layout = calculate_grid_layout(
            canvas_w=render_w,
            canvas_h=render_h,
            num_items=len(image_paths),
            cols=cols,
            rows_per_sheet=rows_per_sheet,
            show_header=show_header,
            show_captions=show_captions,
            margin_x=int(margin_x * r_scale),
            margin_top=int(margin_top * r_scale),
            margin_bottom=int(margin_bottom * r_scale),
            header_height=int(header_height * r_scale),
            spacing_x=int(spacing_x * r_scale),
            spacing_y=int(spacing_y * r_scale),
            caption_height=int(caption_height * r_scale),
            frame_aspect=DEFAULT_FRAME_ASPECT
        )

        # Create canvas
        canvas = Image.new("RGB", (render_w, render_h), theme["canvas_bg"])
        draw = ImageDraw.Draw(canvas)

        # Scale fonts
        title_font_size = max(11, int(105 * scale_factor * r_scale))
        sub_font_size = max(9, int(48 * scale_factor * r_scale))
        caption_font_size = max(10, int(72 * scale_factor * r_scale))
        sub_caption_font_size = max(8, int(30 * scale_factor * r_scale))

        font_bold = get_system_font("bold", title_font_size)
        font_sub = get_system_font("regular", sub_font_size)
        font_mono = get_system_font("mono_bold", caption_font_size)
        font_mono_small = get_system_font("regular", sub_caption_font_size)

        # 1. Render Header
        if show_header:
            hx = layout["start_x"]
            hy = layout["header_y"]
            hw = layout["grid_w"]

            title_text = roll_title.upper() if roll_title else "CONTACT SHEET"
            draw.text((hx, hy), title_text, fill=theme["header_title_color"], font=font_bold)

            meta_parts = []
            if date_str:
                meta_parts.append(f"DATE: {date_str}")
            if film_stock:
                meta_parts.append(f"FILM: {film_stock}")
            if camera_info:
                meta_parts.append(f"GEAR: {camera_info}")
            if notes:
                meta_parts.append(f"NOTE: {notes}")
            meta_parts.append(f"FRAMES: {len(image_paths)}")
            if total_pages > 1:
                meta_parts.append(f"SHEET {page_index + 1} OF {total_pages}")

            sub_text = "   |   ".join(meta_parts)
            sub_y = hy + int(120 * scale_factor * r_scale)
            draw.text((hx, sub_y), sub_text, fill=theme["header_sub_color"], font=font_sub)

            line_y = hy + int(190 * scale_factor * r_scale)
            line_thickness = max(1, int(3 * scale_factor * r_scale))
            draw.line([(hx, line_y), (hx + hw, line_y)], fill=theme["header_line_color"], width=line_thickness)

        # 2. Render Photo Frames & Captions
        boxes = layout["boxes"]
        total_images = len(image_paths)

        for i, img_path in enumerate(image_paths):
            if i >= len(boxes):
                break

            b = boxes[i]
            fx1, fy1, fx2, fy2 = b["frame_box"]
            fw = fx2 - fx1
            fh = fy2 - fy1

            if progress_callback:
                progress_callback(i + 1, total_images, os.path.basename(img_path))

            draw.rectangle([fx1, fy1, fx2, fy2], fill=theme["frame_bg"])

            try:
                if is_preview:
                    if thumbnail_cache is not None and img_path in thumbnail_cache:
                        img = thumbnail_cache[img_path].copy()
                    else:
                        loaded = load_preview_thumbnail(img_path, max_dim=600)
                        if loaded:
                            if thumbnail_cache is not None:
                                thumbnail_cache[img_path] = loaded
                            img = loaded.copy()
                        else:
                            raise RuntimeError(f"Could not decode thumbnail for {img_path}")

                    if rotate_portrait and img.height > img.width:
                        img = img.rotate(90, expand=True)

                    img_w, img_h = img.size
                    img_aspect = img_w / img_h
                    target_aspect = fw / fh

                    if img_aspect > target_aspect:
                        fit_w = fw
                        fit_h = int(fw / img_aspect)
                    else:
                        fit_h = fh
                        fit_w = int(fh * img_aspect)

                    thumb = img.resize((max(1, fit_w), max(1, fit_h)), resample=Image.Resampling.BILINEAR)

                else:
                    with Image.open(img_path) as orig_img:
                        img = ImageOps.exif_transpose(orig_img)

                        if rotate_portrait and img.height > img.width:
                            img = img.rotate(90, expand=True)

                        img_w, img_h = img.size
                        img_aspect = img_w / img_h
                        target_aspect = fw / fh

                        if img_aspect > target_aspect:
                            fit_w = fw
                            fit_h = int(fw / img_aspect)
                        else:
                            fit_h = fh
                            fit_w = int(fh * img_aspect)

                        thumb = img.resize((max(1, fit_w), max(1, fit_h)), resample=Image.Resampling.LANCZOS)

                px = fx1 + (fw - fit_w) // 2
                py = fy1 + (fh - fit_h) // 2

                if thumb.mode != "RGB":
                    thumb = thumb.convert("RGB")

                canvas.paste(thumb, (px, py))

            except Exception as e:
                err_text = f"Error loading\n{os.path.basename(img_path)}"
                draw.rectangle([fx1, fy1, fx2, fy2], fill="#331111" if theme_key == "dark" else "#ffdddd")
                draw.text((fx1 + 10, fy1 + 10), err_text, fill="#ff6666", font=font_mono_small)

            if show_border:
                border_w = max(1, int(2 * scale_factor * r_scale))
                draw.rectangle([fx1, fy1, fx2, fy2], outline=theme["frame_border_color"], width=border_w)

            # 3. Render Frame Labels / Captions
            if show_captions and b["caption_box"]:
                cx1, cy1, cx2, cy2 = b["caption_box"]
                global_frame_num = (page_index * layout["items_per_sheet"]) + i + 1

                if numbering_style == "rebate":
                    text_str = f"{global_frame_num:02d}A"
                    tb = draw.textbbox((cx1 + 4, cy1 + 4), text_str, font=font_mono)
                    th = max(12, tb[3] - tb[1])
                    arrow_w = max(6, int(th * 0.72))
                    arrow_h = max(6, int(th * 0.85))

                    ax = cx1 + 4
                    ay = cy1 + 4 + (th - arrow_h) // 2

                    draw.polygon([
                        (ax, ay),
                        (ax + arrow_w, ay + arrow_h // 2),
                        (ax, ay + arrow_h)
                    ], fill=theme["caption_color"])

                    gap = max(4, int(arrow_w * 0.50))
                    text_x = ax + arrow_w + gap
                    draw.text((text_x, cy1 + 4), text_str, fill=theme["caption_color"], font=font_mono)

                elif numbering_style == "simple":
                    text_str = f"#{global_frame_num:02d}"
                    draw.text((cx1 + 4, cy1 + 4), text_str, fill=theme["caption_color"], font=font_mono)

        return canvas
