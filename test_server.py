import os
import shutil
import tempfile
import threading
import time
import urllib.request
import json
from PIL import Image

from server import ThreadedHTTPServer, AppRequestHandler

def run_integration_test():
    test_dir = tempfile.mkdtemp(prefix="fpo_srv_test_")
    out_dir = tempfile.mkdtemp(prefix="fpo_srv_out_")
    dummy_files = []

    try:
        for i in range(1, 4):
            path = os.path.join(test_dir, f"IMG_{i:04d}.jpg")
            img = Image.new("RGB", (400, 300), color=(100, 50 * i, 200))
            img.save(path)
            dummy_files.append(path)

        port = 8899
        server = ThreadedHTTPServer(("127.0.0.1", port), AppRequestHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.3)

        base_url = f"http://127.0.0.1:{port}"

        # 1. Test GET /
        req = urllib.request.urlopen(f"{base_url}/")
        assert req.status == 200
        html = req.read().decode('utf-8')
        assert "FILM PHOTO ORGANIZER" in html
        print("[✓] GET /: OK")

        # 2. Test GET /api/config
        req = urllib.request.urlopen(f"{base_url}/api/config")
        assert req.status == 200
        config_data = json.loads(req.read().decode('utf-8'))
        assert "canvas_presets" in config_data
        print("[✓] GET /api/config: OK")

        # 3. Test POST /api/organizer/analyze
        post_data = json.dumps({"folder_path": test_dir}).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/organizer/analyze", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        org_data = json.loads(resp.read().decode('utf-8'))
        assert org_data["count"] == 3
        print("[✓] POST /api/organizer/analyze: OK")

        # 4. Test POST /api/organizer/preview-names
        post_data = json.dumps({
            "files": ["IMG_0001.jpg", "IMG_0002.jpg", "IMG_0003.jpg"],
            "date_str": "2026-08-21",
            "film_stock": "Kodak Portra 400",
            "reverse_order": False
        }).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/organizer/preview-names", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        pairs_data = json.loads(resp.read().decode('utf-8'))
        assert pairs_data["pairs"][0]["new_name"] == "2026-08-21_Kodak-Portra-400_01.jpg"
        print("[✓] POST /api/organizer/preview-names: OK")

        # 5. Test POST /api/contact/scan
        post_data = json.dumps({"folder_path": test_dir}).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/contact/scan", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        contact_scan = json.loads(resp.read().decode('utf-8'))
        assert contact_scan["count"] == 3
        print("[✓] POST /api/contact/scan: OK")

        # 6. Test POST /api/contact/preview
        post_data = json.dumps({
            "config": {
                "canvas_width": 4000,
                "canvas_height": 3200,
                "columns": 3,
                "rows_per_sheet": 2,
                "theme": "dark"
            },
            "photos": dummy_files,
            "page_index": 0,
            "preview_scale": 0.1
        }).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/contact/preview", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        preview_res = json.loads(resp.read().decode('utf-8'))
        assert "data:image/jpeg;base64," in preview_res["image"]
        print("[✓] POST /api/contact/preview: OK")

        # 7. Test POST /api/contact/generate (with job_id)
        job_id = "test_job_123"
        post_data = json.dumps({
            "config": {
                "canvas_width": 4000,
                "canvas_height": 3200,
                "columns": 3,
                "rows_per_sheet": 2,
                "theme": "dark"
            },
            "photos": dummy_files,
            "output_dir": out_dir,
            "format": "JPEG",
            "quality": 85,
            "job_id": job_id
        }).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/contact/generate", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        gen_res = json.loads(resp.read().decode('utf-8'))
        assert gen_res["success"] is True
        assert len(gen_res["saved_files"]) == 1
        assert os.path.exists(gen_res["saved_files"][0])
        print("[✓] POST /api/contact/generate (with Job ID): OK")

        # 8. Test GET /api/jobs/<job_id>
        job_req = urllib.request.urlopen(f"{base_url}/api/jobs/{job_id}")
        assert job_req.status == 200
        job_info = json.loads(job_req.read().decode('utf-8'))
        assert job_info["status"] == "completed"
        assert job_info["percent"] == 100
        print("[✓] GET /api/jobs/<job_id> (Job state tracker): OK")

        # 9. Test POST /api/organizer/process (with job_id)
        org_job_id = "test_org_job_456"
        post_data = json.dumps({
            "mode": "copy",
            "source_path": test_dir,
            "output_parent": out_dir,
            "date_str": "2026-08-21",
            "film_stock": "Portra400",
            "reverse_order": False,
            "files": ["IMG_0001.jpg", "IMG_0002.jpg", "IMG_0003.jpg"],
            "job_id": org_job_id
        }).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/organizer/process", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        org_res = json.loads(resp.read().decode('utf-8'))
        assert org_res["success_count"] == 3
        print("[✓] POST /api/organizer/process (with Job ID): OK")

        # 10. Test GET /api/thumbnail
        thumb_url = f"{base_url}/api/thumbnail?path={urllib.parse.quote(dummy_files[0])}&size=200"
        req = urllib.request.urlopen(thumb_url)
        assert req.status == 200
        assert req.headers.get("Content-Type") == "image/jpeg"
        print("[✓] GET /api/thumbnail: OK")

        # 11. Test POST /api/resolve-path
        post_data = json.dumps({"path": test_dir}).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/resolve-path", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        resolve_res = json.loads(resp.read().decode('utf-8'))
        assert resolve_res["valid"] is True
        assert resolve_res["is_dir"] is True
        print("[✓] POST /api/resolve-path: OK")

        # 10. Test POST /api/upload-dropped
        sample_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        post_data = json.dumps({
            "folder_name": "test_dropped_roll",
            "files": [{"name": "drop_1.png", "data": sample_b64}]
        }).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/upload-dropped", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        up_res = json.loads(resp.read().decode('utf-8'))
        assert up_res["success"] is True
        # 12. Test POST /api/locate-dropped-folder
        post_data = json.dumps({
            "folder_name": os.path.basename(test_dir),
            "filenames": ["IMG_0001.jpg", "IMG_0002.jpg"]
        }).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/api/locate-dropped-folder", data=post_data, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        assert resp.status == 200
        locate_res = json.loads(resp.read().decode('utf-8'))
        assert locate_res["found"] is True
        assert os.path.exists(locate_res["path"])
        print("[✓] POST /api/locate-dropped-folder (Auto-find original folder): OK")

        # 13. Test 404 Not Found error handling and logging
        try:
            urllib.request.urlopen(f"{base_url}/non_existent_page.html")
        except urllib.error.HTTPError as e:
            assert e.code == 404
            print("[✓] GET /non_existent_page.html (404 handling): OK")

        print("\nALL 12 INTEGRATION TESTS PASSED SUCCESSFULLY!")

    finally:
        server.shutdown()
        shutil.rmtree(test_dir, ignore_errors=True)
        shutil.rmtree(out_dir, ignore_errors=True)

if __name__ == "__main__":
    run_integration_test()


