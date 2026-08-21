import os
import shutil
import datetime
from config import IMAGE_EXTENSIONS
from utils import parse_folder_metadata, sanitize_filename


class PhotoOrganizer:
    """
    Core engine for analyzing, cataloging, batch renaming, and safe-copying
    analog film scans and digital photographs.
    """

    @staticmethod
    def analyze_folder(folder_path: str) -> dict:
        if not folder_path or not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")

        folder_name = os.path.basename(os.path.normpath(folder_path))
        roll_title, date_str, film_stock = parse_folder_metadata(folder_path)

        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")

        matched_files = []
        try:
            entries = sorted(os.listdir(folder_path))
            for entry in entries:
                full_path = os.path.join(folder_path, entry)
                if os.path.isfile(full_path) and entry.lower().endswith(IMAGE_EXTENSIONS):
                    matched_files.append(entry)
        except Exception as e:
            raise RuntimeError(f"Error reading folder: {e}")

        return {
            "folder_path": os.path.normpath(folder_path),
            "folder_name": folder_name,
            "date_str": date_str,
            "film_stock": film_stock,
            "roll_title": roll_title,
            "files": matched_files,
            "count": len(matched_files)
        }

    @staticmethod
    def compute_file_pairs(matched_files: list, date_str: str, film_stock: str, reverse_order: bool = False) -> tuple:
        clean_date = date_str.strip() or datetime.date.today().strftime("%Y-%m-%d")
        clean_film = film_stock.strip()
        film_dashed = clean_film.replace(' ', '-') if clean_film else "Film-Stock"

        files_to_process = list(reversed(matched_files)) if reverse_order else list(matched_files)

        pairs = []
        for i, filename in enumerate(files_to_process, 1):
            ext = os.path.splitext(filename)[1].lower()
            new_name = f"{clean_date}_{film_dashed}_{i:02d}{ext}"
            pairs.append({
                "original": filename,
                "new_name": new_name,
                "index": i
            })

        new_folder_name = f"isopatrusute_{clean_date}_{clean_film}" if clean_film else f"isopatrusute_{clean_date}"
        new_folder_name = sanitize_filename(new_folder_name)

        return pairs, new_folder_name

    @staticmethod
    def run_in_place_rename(source_path: str, new_folder_name: str, file_pairs: list, progress_callback=None) -> dict:
        source_path = os.path.normpath(source_path)
        parent_dir = os.path.dirname(source_path)
        total_files = len(file_pairs)
        success_count = 0
        error_count = 0
        errors = []

        # To avoid collisions when renaming files (e.g. file1 -> file2 while file2 exists),
        # use a two-pass rename with temporary staging names if needed
        staging_map = []
        for item in file_pairs:
            old_name = item["original"]
            new_name = item["new_name"]
            if old_name != new_name:
                temp_name = f"__tmp_ren_{item['index']}_{old_name}"
                staging_map.append((old_name, temp_name, new_name))
            else:
                staging_map.append((old_name, None, new_name))

        # Pass 1: Rename to temporary names to prevent clobbering
        for i, (old_name, temp_name, new_name) in enumerate(staging_map):
            if temp_name:
                try:
                    src = os.path.join(source_path, old_name)
                    tmp = os.path.join(source_path, temp_name)
                    if os.path.exists(src):
                        os.rename(src, tmp)
                except Exception as e:
                    error_count += 1
                    errors.append(f"Staging error on {old_name}: {str(e)}")

        # Pass 2: Rename from temporary (or original) to final target name
        for i, (old_name, temp_name, new_name) in enumerate(staging_map):
            try:
                curr_src = os.path.join(source_path, temp_name if temp_name else old_name)
                final_dst = os.path.join(source_path, new_name)
                if os.path.exists(curr_src):
                    os.rename(curr_src, final_dst)
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"File not found during final rename: {curr_src}")
            except Exception as e:
                error_count += 1
                errors.append(f"Error renaming {old_name} -> {new_name}: {str(e)}")

            if progress_callback:
                progress_callback(i + 1, total_files, new_name)

        # 3. Rename the parent folder if desired and different
        folder_renamed = False
        final_folder_path = source_path
        if new_folder_name:
            target_folder_path = os.path.join(parent_dir, new_folder_name)
            if source_path != target_folder_path:
                try:
                    os.rename(source_path, target_folder_path)
                    folder_renamed = True
                    final_folder_path = target_folder_path
                except Exception as e:
                    errors.append(f"Could not rename folder: {str(e)}")

        return {
            "success_count": success_count,
            "error_count": error_count,
            "folder_renamed": folder_renamed,
            "final_folder_path": final_folder_path,
            "errors": errors
        }

    @staticmethod
    def run_safe_copy(source_path: str, output_parent: str, new_folder_name: str, file_pairs: list, progress_callback=None) -> dict:
        source_path = os.path.normpath(source_path)
        output_parent = os.path.normpath(output_parent) if output_parent else os.path.dirname(source_path)
        target_folder = os.path.join(output_parent, new_folder_name)

        os.makedirs(target_folder, exist_ok=True)

        total_files = len(file_pairs)
        success_count = 0
        error_count = 0
        errors = []

        for i, item in enumerate(file_pairs):
            old_name = item["original"]
            new_name = item["new_name"]
            src_file = os.path.join(source_path, old_name)
            dst_file = os.path.join(target_folder, new_name)

            try:
                if os.path.exists(src_file):
                    shutil.copy2(src_file, dst_file)
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"Source file not found: {src_file}")
            except Exception as e:
                error_count += 1
                errors.append(f"Error copying {old_name}: {str(e)}")

            if progress_callback:
                progress_callback(i + 1, total_files, new_name)

        return {
            "success_count": success_count,
            "error_count": error_count,
            "folder_created": True,
            "final_folder_path": target_folder,
            "errors": errors
        }
