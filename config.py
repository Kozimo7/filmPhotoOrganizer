import os

# Contact Sheet Dimensions & Layout Defaults
DEFAULT_CANVAS_WIDTH = 11500
DEFAULT_CANVAS_HEIGHT = 9200
DEFAULT_COLUMNS = 6
DEFAULT_ROWS_PER_SHEET = 6
DEFAULT_FRAME_ASPECT = 1.5  # Standard 3:2 35mm film frame
DEFAULT_ROTATE_PORTRAIT = False

IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif', '.webp', '.dng')

CANVAS_PRESETS = {
    "11500 x 9200 (Archival Master - Default)": (11500, 9200),
    "8000 x 6400 (Standard Large Print)": (8000, 6400),
    "5750 x 4600 (Medium Print)": (5750, 4600),
    "4000 x 3200 (Screen / Web Preview)": (4000, 3200),
    "Custom Dimensions": (11500, 9200)
}

THEMES = {
    "dark": {
        "name": "Classic Darkroom Black",
        "canvas_bg": "#0a0a0a",
        "header_title_color": "#ffffff",
        "header_sub_color": "#b0b0b0",
        "header_line_color": "#2c2c2c",
        "frame_bg": "#050505",
        "frame_border_color": "#282828",
        "caption_color": "#d0d0d0",
        "caption_sub_color": "#888888",
        "footer_color": "#555555"
    },
    "light": {
        "name": "Clean Modern White",
        "canvas_bg": "#ffffff",
        "header_title_color": "#111111",
        "header_sub_color": "#444444",
        "header_line_color": "#e0e0e0",
        "frame_bg": "#f8f8f8",
        "frame_border_color": "#d5d5d5",
        "caption_color": "#222222",
        "caption_sub_color": "#777777",
        "footer_color": "#999999"
    }
}

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
