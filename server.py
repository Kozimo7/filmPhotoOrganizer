import os
import io
import sys
import json
import base64
import urllib.parse
import platform
import subprocess
import threading
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

from config import (
    DEFAULT_CANVAS_WIDTH,
    DEFAULT_CANVAS_HEIGHT,
    DEFAULT_COLUMNS,
    DEFAULT_ROWS_PER_SHEET,
    IMAGE_EXTENSIONS,
    CANVAS_PRESETS,
    THEMES,
    DEFAULT_HOST,
    DEFAULT_PORT
)
from utils import (
    parse_folder_metadata,
    determine_auto_grid,
    calculate_grid_layout,
    load_preview_thumbnail,
    reveal_in_file_manager,
    sanitize_filename
)
from generator import ContactSheetGenerator
from organizer import PhotoOrganizer

# In-memory thumbnail cache for fast live contact sheet preview
THUMBNAIL_CACHE = {}


def pick_native_folder(title="Select Folder", initial_dir=None) -> str:
    """Trigger native OS folder selection dialog."""
    system_name = platform.system()
    if system_name == "Darwin":
        try:
            cmd = ['osascript', '-e', f'POSIX path of (choose folder with prompt "{title}")']
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip().rstrip('/')
        except Exception:
            pass

    # Fallback to Tkinter
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title=title, initialdir=initial_dir or os.path.expanduser("~"))
        root.destroy()
        return os.path.normpath(folder) if folder else ""
    except Exception as e:
        print(f"Tkinter dialog error: {e}")
        return ""


def pick_native_files(title="Select Photo Files", initial_dir=None) -> list:
    """Trigger native OS file selection dialog."""
    system_name = platform.system()
    if system_name == "Darwin":
        try:
            cmd = ['osascript', '-e', f'set f to choose file with prompt "{title}" of type {{"public.image"}} with multiple selections allowed\nset out to ""\nrepeat with anItem in f\nset out to out & (POSIX path of anItem) & linefeed\nend repeat\nreturn out']
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return [p.strip() for p in res.stdout.strip().split("\n") if p.strip()]
        except Exception:
            pass

    # Fallback to Tkinter
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        filetypes = [("Image files", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp *.dng"), ("All files", "*.*")]
        files = filedialog.askopenfilenames(title=title, initialdir=initial_dir or os.path.expanduser("~"), filetypes=filetypes)
        root.destroy()
        return [os.path.normpath(f) for f in files] if files else []
    except Exception as e:
        print(f"Tkinter dialog error: {e}")
        return []


def locate_local_folder(folder_name: str, sample_files: list = None) -> str:
    """Search common user directories for a dropped folder by name and sample contents."""
    if not folder_name:
        return ""

    clean_name = folder_name.strip().strip('"').strip("'")
    home = os.path.expanduser("~")
    search_roots = [
        os.path.join(home, "Downloads"),
        os.path.join(home, "Pictures"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
        home,
        os.getcwd(),
        os.path.dirname(os.getcwd()),
        tempfile.gettempdir()
    ]

    # Windows drive roots
    if platform.system() == "Windows":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                search_roots.append(drive)

    for root in search_roots:
        if not os.path.exists(root):
            continue

        # 1. Direct check: root / folder_name
        direct = os.path.join(root, clean_name)
        if os.path.isdir(direct):
            if not sample_files or any(os.path.exists(os.path.join(direct, f)) for f in sample_files):
                return os.path.normpath(direct)

        # 2. Case-insensitive search 1-level deep in primary user directories
        if root in [os.path.join(home, "Downloads"), os.path.join(home, "Pictures"), os.path.join(home, "Desktop"), os.path.join(home, "Documents")]:
            try:
                for entry in os.listdir(root):
                    sub = os.path.join(root, entry)
                    if os.path.isdir(sub) and entry.lower() == clean_name.lower():
                        if not sample_files or any(os.path.exists(os.path.join(sub, f)) for f in sample_files):
                            return os.path.normpath(sub)
            except Exception:
                pass

    return ""


JOB_TRACKER = {}
JOB_LOCK = threading.Lock()


def set_job_progress(job_id: str, current: int, total: int, filename: str = "", sheet: int = 1, total_sheets: int = 1, extra_msg: str = ""):
    if not job_id:
        return
    pct = int((current / total) * 100) if total > 0 else 0
    if extra_msg:
        msg = extra_msg
    else:
        msg = f"Rendering frame {current}/{total} ({pct}%): {filename}"
        if total_sheets > 1:
            msg += f" [Sheet {sheet}/{total_sheets}]"

    with JOB_LOCK:
        JOB_TRACKER[job_id] = {
            "status": "running",
            "current": current,
            "total": total,
            "percent": pct,
            "filename": filename,
            "sheet": sheet,
            "total_sheets": total_sheets,
            "message": msg
        }


def finish_job(job_id: str, result_data: dict = None, error: str = None):
    if not job_id:
        return
    with JOB_LOCK:
        if error:
            JOB_TRACKER[job_id] = {
                "status": "error",
                "percent": 0,
                "error": str(error),
                "message": f"Error: {error}"
            }
        else:
            JOB_TRACKER[job_id] = {
                "status": "completed",
                "percent": 100,
                "message": "Completed successfully.",
                "result": result_data
            }


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class AppRequestHandler(SimpleHTTPRequestHandler):
    """Handles static web assets and RESTful API endpoints."""

    def __init__(self, *args, **kwargs):
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        super().__init__(*args, directory=static_dir, **kwargs)

    def log_message(self, format, *args):
        # Concise logging for API calls
        try:
            msg = format % args
            if "/api/thumbnail" in msg or "/api/contact/preview" in msg or "/api/jobs/" in msg:
                return
            super().log_message(format, *args)
        except Exception:
            super().log_message(format, *args)

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self) -> dict:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode('utf-8')
        return json.loads(raw)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if path.startswith("/api/jobs/"):
            job_id = path[len("/api/jobs/"):]
            with JOB_LOCK:
                job_info = JOB_TRACKER.get(job_id, {"status": "running", "percent": 0, "message": "Initializing..."})
            self.send_json(job_info)
            return

        if path == "/api/config":
            self.send_json({
                "canvas_presets": CANVAS_PRESETS,
                "themes": THEMES,
                "default_width": DEFAULT_CANVAS_WIDTH,
                "default_height": DEFAULT_CANVAS_HEIGHT,
                "default_columns": DEFAULT_COLUMNS,
                "default_rows": DEFAULT_ROWS_PER_SHEET,
                "extensions": list(IMAGE_EXTENSIONS)
            })
            return

        elif path == "/api/thumbnail":
            img_path = query.get("path", [""])[0]
            if not img_path or not os.path.exists(img_path):
                self.send_response(404)
                self.end_headers()
                return

            max_size = int(query.get("size", [300])[0])
            thumb = load_preview_thumbnail(img_path, max_dim=max_size)
            if not thumb:
                self.send_response(500)
                self.end_headers()
                return

            buf = io.BytesIO()
            thumb.save(buf, format="JPEG", quality=80)
            img_bytes = buf.getvalue()

            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(img_bytes)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(img_bytes)
            return

        # Default static file handler
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            data = self.read_json_body()

            # 1. Native File / Folder Browsers & Path Resolvers
            if path == "/api/browse/folder":
                title = data.get("title", "Select Folder")
                initial_dir = data.get("initial_dir")
                chosen = pick_native_folder(title=title, initial_dir=initial_dir)
                self.send_json({"path": chosen or ""})
                return

            elif path == "/api/browse/files":
                title = data.get("title", "Select Photo Files")
                initial_dir = data.get("initial_dir")
                chosen = pick_native_files(title=title, initial_dir=initial_dir)
                self.send_json({"files": chosen or []})
                return

            elif path == "/api/resolve-path":
                raw_path = data.get("path", "").strip().strip('"').strip("'")
                if raw_path.startswith("file:///"):
                    raw_path = urllib.parse.unquote(raw_path[8:])
                elif raw_path.startswith("file://"):
                    raw_path = urllib.parse.unquote(raw_path[7:])
                
                raw_path = os.path.normpath(raw_path)
                if os.path.exists(raw_path):
                    is_dir = os.path.isdir(raw_path)
                    dir_path = raw_path if is_dir else os.path.dirname(raw_path)
                    self.send_json({
                        "valid": True,
                        "path": dir_path,
                        "file_path": raw_path if not is_dir else "",
                        "is_dir": is_dir
                    })
                else:
                    self.send_json({"valid": False, "path": raw_path})
                return

            elif path == "/api/locate-dropped-folder":
                folder_name = data.get("folder_name", "").strip()
                filenames = data.get("filenames", [])
                found_path = locate_local_folder(folder_name, filenames)
                self.send_json({
                    "found": bool(found_path),
                    "path": found_path or ""
                })
                return

            elif path == "/api/upload-dropped":
                folder_name = data.get("folder_name", "dropped_roll").strip()
                folder_name = sanitize_filename(folder_name) or "dropped_roll"
                files = data.get("files", [])

                if not files:
                    self.send_json({"error": "No files provided"}, status=400)
                    return

                downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                staging_base = os.path.join(downloads_dir, "FilmPhotoStaging") if os.path.exists(downloads_dir) else os.path.join(tempfile.gettempdir(), "fpo_staging")
                staging_dir = os.path.join(staging_base, folder_name)
                os.makedirs(staging_dir, exist_ok=True)

                saved_files = []
                for item in files:
                    fname = os.path.basename(item.get("name", "photo.jpg"))
                    b64_data = item.get("data", "")
                    if "," in b64_data:
                        b64_data = b64_data.split(",", 1)[1]

                    file_bytes = base64.b64decode(b64_data)
                    out_file_path = os.path.join(staging_dir, fname)
                    with open(out_file_path, "wb") as f:
                        f.write(file_bytes)
                    saved_files.append(out_file_path)

                self.send_json({
                    "success": True,
                    "folder_path": staging_dir,
                    "count": len(saved_files),
                    "files": saved_files
                })
                return

            # 2. Photo Organizer Endpoints
            elif path == "/api/organizer/analyze":
                folder_path = data.get("folder_path", "").strip()
                if not folder_path or not os.path.exists(folder_path):
                    self.send_json({"error": "Folder does not exist"}, status=400)
                    return

                res = PhotoOrganizer.analyze_folder(folder_path)
                pairs, new_folder_name = PhotoOrganizer.compute_file_pairs(
                    res["files"], res["date_str"], res["film_stock"], reverse_order=False
                )
                res["pairs"] = pairs
                res["new_folder_name"] = new_folder_name
                self.send_json(res)
                return

            elif path == "/api/organizer/preview-names":
                files = data.get("files", [])
                date_str = data.get("date_str", "")
                film_stock = data.get("film_stock", "")
                reverse_order = bool(data.get("reverse_order", False))

                pairs, new_folder_name = PhotoOrganizer.compute_file_pairs(
                    files, date_str, film_stock, reverse_order=reverse_order
                )
                self.send_json({"pairs": pairs, "new_folder_name": new_folder_name})
                return

            elif path == "/api/organizer/process":
                mode = data.get("mode", "inplace")
                source_path = data.get("source_path", "").strip()
                output_parent = data.get("output_parent", "").strip()
                date_str = data.get("date_str", "").strip()
                film_stock = data.get("film_stock", "").strip()
                reverse_order = bool(data.get("reverse_order", False))
                files = data.get("files", [])
                job_id = data.get("job_id", "")

                if not source_path or not os.path.exists(source_path):
                    if job_id:
                        finish_job(job_id, error="Source path does not exist")
                    self.send_json({"error": "Source path does not exist"}, status=400)
                    return

                if not files:
                    # Scan files directly
                    res = PhotoOrganizer.analyze_folder(source_path)
                    files = res["files"]

                pairs, new_folder_name = PhotoOrganizer.compute_file_pairs(
                    files, date_str, film_stock, reverse_order=reverse_order
                )

                total_items = len(pairs)
                if job_id:
                    set_job_progress(job_id, 0, total_items, "", extra_msg="Starting photo batch processing...")

                def progress_cb(current, total, filename):
                    action = "Renaming" if mode == "inplace" else "Copying"
                    pct = int((current / total) * 100) if total > 0 else 0
                    msg = f"{action} photo {current}/{total} ({pct}%): {filename}"
                    set_job_progress(job_id, current, total, filename, extra_msg=msg)

                if mode == "inplace":
                    result = PhotoOrganizer.run_in_place_rename(source_path, new_folder_name, pairs, progress_callback=progress_cb)
                else:
                    result = PhotoOrganizer.run_safe_copy(source_path, output_parent, new_folder_name, pairs, progress_callback=progress_cb)

                if job_id:
                    finish_job(job_id, result)

                self.send_json(result)
                return

            # 3. Contact Sheet Endpoints
            elif path == "/api/contact/scan":
                folder_path = data.get("folder_path", "").strip()
                custom_files = data.get("files", [])

                found_images = []
                roll_title = "ANALOG ROLL"
                date_str = ""
                film_stock = ""

                if folder_path and os.path.exists(folder_path):
                    roll_title, date_str, film_stock = parse_folder_metadata(folder_path)
                    try:
                        for entry in sorted(os.listdir(folder_path)):
                            full_path = os.path.join(folder_path, entry)
                            if os.path.isfile(full_path) and entry.lower().endswith(IMAGE_EXTENSIONS):
                                found_images.append(full_path)
                    except Exception as e:
                        self.send_json({"error": str(e)}, status=500)
                        return
                elif custom_files:
                    found_images = [f for f in custom_files if os.path.exists(f) and f.lower().endswith(IMAGE_EXTENSIONS)]
                    if found_images:
                        roll_title, date_str, film_stock = parse_folder_metadata(os.path.dirname(found_images[0]))

                # Gather dimensions and orientations
                from PIL import Image
                photo_details = []
                for p in found_images:
                    w, h, orient = 0, 0, "Land"
                    try:
                        with Image.open(p) as img:
                            w, h = img.size
                            orient = "Port" if h > w else "Land"
                    except Exception:
                        pass
                    photo_details.append({
                        "path": p,
                        "filename": os.path.basename(p),
                        "width": w,
                        "height": h,
                        "orientation": orient
                    })

                canvas_w = int(data.get("canvas_width", DEFAULT_CANVAS_WIDTH))
                canvas_h = int(data.get("canvas_height", DEFAULT_CANVAS_HEIGHT))
                auto_cols, auto_rows = determine_auto_grid(len(found_images), canvas_w, canvas_h)

                self.send_json({
                    "photos": photo_details,
                    "count": len(photo_details),
                    "roll_title": roll_title,
                    "date_str": date_str,
                    "film_stock": film_stock,
                    "auto_cols": auto_cols,
                    "auto_rows": auto_rows
                })
                return

            elif path == "/api/contact/preview":
                config = data.get("config", {})
                photos = data.get("photos", [])
                page_index = int(data.get("page_index", 0))
                preview_scale = float(data.get("preview_scale", 0.12))

                cols = int(config.get("columns", DEFAULT_COLUMNS))
                rows = int(config.get("rows_per_sheet", DEFAULT_ROWS_PER_SHEET))
                per_sheet = max(1, cols * rows)
                total_pages = max(1, (len(photos) + per_sheet - 1) // per_sheet) if photos else 1

                page_index = max(0, min(page_index, total_pages - 1))
                page_photos = photos[page_index * per_sheet:(page_index + 1) * per_sheet]

                generator = ContactSheetGenerator(config)
                sheet_img = generator.render_sheet(
                    image_paths=page_photos,
                    page_index=page_index,
                    total_pages=total_pages,
                    is_preview=True,
                    preview_scale=preview_scale,
                    thumbnail_cache=THUMBNAIL_CACHE
                )

                buf = io.BytesIO()
                sheet_img.save(buf, format="JPEG", quality=85)
                b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')

                self.send_json({
                    "image": f"data:image/jpeg;base64,{b64_str}",
                    "width": sheet_img.width,
                    "height": sheet_img.height,
                    "page_index": page_index,
                    "total_pages": total_pages,
                    "photos_on_sheet": len(page_photos)
                })
                return

            elif path == "/api/contact/generate":
                config = data.get("config", {})
                photos = data.get("photos", [])
                output_dir = data.get("output_dir", "").strip()
                out_format = data.get("format", "JPEG").upper()
                quality = int(data.get("quality", 95))
                job_id = data.get("job_id", "")

                if not photos:
                    if job_id:
                        finish_job(job_id, error="No photos provided")
                    self.send_json({"error": "No photos provided"}, status=400)
                    return

                if not output_dir or not os.path.exists(output_dir):
                    # Default to directory of first photo
                    output_dir = os.path.dirname(photos[0]) if photos else os.path.expanduser("~")

                cols = int(config.get("columns", DEFAULT_COLUMNS))
                rows = int(config.get("rows_per_sheet", DEFAULT_ROWS_PER_SHEET))
                per_sheet = max(1, cols * rows)
                total_pages = max(1, (len(photos) + per_sheet - 1) // per_sheet)
                total_photos = len(photos)

                if job_id:
                    set_job_progress(job_id, 0, total_photos, "", sheet=1, total_sheets=total_pages, extra_msg="Initializing contact sheet generator...")

                generator = ContactSheetGenerator(config)
                saved_files = []

                for page_idx in range(total_pages):
                    page_photos = photos[page_idx * per_sheet:(page_idx + 1) * per_sheet]

                    def on_progress(cur, total, filename):
                        overall_idx = page_idx * per_sheet + cur
                        set_job_progress(job_id, overall_idx, total_photos, filename, sheet=page_idx + 1, total_sheets=total_pages)

                    sheet_img = generator.render_sheet(
                        image_paths=page_photos,
                        page_index=page_idx,
                        total_pages=total_pages,
                        is_preview=False,
                        progress_callback=on_progress
                    )

                    ext = "jpg" if out_format == "JPEG" else "png"
                    if total_pages == 1:
                        filename = f"0contact_sheet.{ext}"
                    else:
                        filename = f"0contact_sheet_p{page_idx + 1}.{ext}"

                    if job_id:
                        set_job_progress(job_id, min(total_photos, (page_idx + 1) * per_sheet), total_photos, filename, sheet=page_idx + 1, total_sheets=total_pages, extra_msg=f"Saving master contact sheet {page_idx + 1}/{total_pages}: {filename}...")

                    dest_path = os.path.join(output_dir, filename)
                    if out_format == "JPEG":
                        sheet_img.save(dest_path, format="JPEG", quality=quality, subsampling=0)
                    else:
                        sheet_img.save(dest_path, format="PNG", optimize=True)

                    saved_files.append(dest_path)

                result = {
                    "success": True,
                    "saved_files": saved_files,
                    "output_dir": output_dir,
                    "count": len(saved_files)
                }

                if job_id:
                    finish_job(job_id, result)

                self.send_json(result)
                return

            # 4. System utilities
            elif path == "/api/system/open-folder":
                target_path = data.get("path", "").strip()
                if not target_path or not os.path.exists(target_path):
                    self.send_json({"error": "Path does not exist"}, status=400)
                    return

                success = reveal_in_file_manager(target_path)
                self.send_json({"success": success})
                return

            else:
                self.send_json({"error": "Not Found"}, status=404)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_json({"error": str(e)}, status=500)


def run_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, AppRequestHandler)
    print(f"Film Photo Organizer Server running at http://{host}:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
