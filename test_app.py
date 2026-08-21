import os
import shutil
import tempfile
import unittest
from PIL import Image

from config import DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT, THEMES
from utils import parse_folder_metadata, determine_auto_grid, get_system_font, load_preview_thumbnail
from generator import ContactSheetGenerator
from organizer import PhotoOrganizer


class TestFilmPhotoOrganizer(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="fpo_test_")
        # Create 5 dummy test images
        self.test_images = []
        for i in range(1, 6):
            img_path = os.path.join(self.test_dir, f"scan_frame_{i:02d}.jpg")
            img = Image.new("RGB", (800, 600) if i % 2 == 0 else (600, 800), color=(50 * i, 30 * i, 100))
            img.save(img_path, format="JPEG")
            self.test_images.append(img_path)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_metadata_parsing(self):
        title, date_str, film = parse_folder_metadata("isopatrusute_order-50189_2026-08-20_Portra_400")
        self.assertEqual(date_str, "2026-08-20")
        self.assertIn("Portra 400", film)

        title2, date_str2, film2 = parse_folder_metadata("2026-05-15_Kodak_Gold_200")
        self.assertEqual(date_str2, "2026-05-15")
        self.assertIn("Kodak Gold 200", film2)

    def test_auto_grid(self):
        cols36, rows36 = determine_auto_grid(36, 11500, 9200)
        self.assertEqual((cols36, rows36), (6, 6))

        cols40, rows40 = determine_auto_grid(40, 11500, 9200)
        self.assertIn((cols40, rows40), [(8, 5), (5, 8)])

    def test_fonts(self):
        font_bold = get_system_font("bold", 30)
        self.assertIsNotNone(font_bold)
        font_mono = get_system_font("mono", 24)
        self.assertIsNotNone(font_mono)

    def test_generator_preview_and_master(self):
        config = {
            "canvas_width": 4000,
            "canvas_height": 3200,
            "columns": 3,
            "rows_per_sheet": 2,
            "theme": "dark",
            "roll_title": "TEST ROLL",
            "date_str": "2026-08-21",
            "film_stock": "Kodak Tri-X 400",
            "show_header": True,
            "show_captions": True,
            "rotate_portrait": True
        }
        generator = ContactSheetGenerator(config)

        # 1. Preview render
        preview = generator.render_sheet(self.test_images, is_preview=True, preview_scale=0.15)
        self.assertIsNotNone(preview)
        self.assertEqual(preview.width, int(4000 * 0.15))
        self.assertEqual(preview.height, int(3200 * 0.15))

        # 2. Master render
        master = generator.render_sheet(self.test_images, is_preview=False)
        self.assertIsNotNone(master)
        self.assertEqual(master.width, 4000)
        self.assertEqual(master.height, 3200)

    def test_organizer_analyze_and_pairs(self):
        analysis = PhotoOrganizer.analyze_folder(self.test_dir)
        self.assertEqual(analysis["count"], 5)

        pairs, new_folder = PhotoOrganizer.compute_file_pairs(
            analysis["files"], "2026-08-21", "Portra 400", reverse_order=False
        )
        self.assertEqual(len(pairs), 5)
        self.assertEqual(pairs[0]["new_name"], "2026-08-21_Portra-400_01.jpg")
        self.assertEqual(pairs[4]["new_name"], "2026-08-21_Portra-400_05.jpg")
        self.assertEqual(new_folder, "isopatrusute_2026-08-21_Portra 400")

    def test_organizer_safe_copy(self):
        analysis = PhotoOrganizer.analyze_folder(self.test_dir)
        pairs, new_folder = PhotoOrganizer.compute_file_pairs(
            analysis["files"], "2026-08-21", "Portra 400", reverse_order=False
        )
        out_parent = tempfile.mkdtemp(prefix="fpo_out_")
        try:
            res = PhotoOrganizer.run_safe_copy(self.test_dir, out_parent, new_folder, pairs)
            self.assertEqual(res["success_count"], 5)
            self.assertEqual(res["error_count"], 0)
            self.assertTrue(os.path.exists(res["final_folder_path"]))
            copied_files = os.listdir(res["final_folder_path"])
            self.assertEqual(len(copied_files), 5)
            self.assertIn("2026-08-21_Portra-400_01.jpg", copied_files)
        finally:
            if os.path.exists(out_parent):
                shutil.rmtree(out_parent)

    def test_organizer_inplace_rename(self):
        analysis = PhotoOrganizer.analyze_folder(self.test_dir)
        pairs, new_folder = PhotoOrganizer.compute_file_pairs(
            analysis["files"], "2026-08-21", "Gold 200", reverse_order=True
        )
        res = PhotoOrganizer.run_in_place_rename(self.test_dir, new_folder, pairs)
        self.assertEqual(res["success_count"], 5)
        self.assertEqual(res["error_count"], 0)
        self.assertTrue(os.path.exists(res["final_folder_path"]))
        # In reverse order, original scan_frame_05.jpg became 2026-08-21_Gold-200_01.jpg
        renamed_files = os.listdir(res["final_folder_path"])
        self.assertIn("2026-08-21_Gold-200_01.jpg", renamed_files)
        self.assertIn("2026-08-21_Gold-200_05.jpg", renamed_files)
        # update test_dir for cleanup
        self.test_dir = res["final_folder_path"]


if __name__ == "__main__":
    unittest.main()
