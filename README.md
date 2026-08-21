# Film Photo Organizer & Archival Contact Sheet Generator

A unified, modern web-based desktop application for analog film photographers and digital archivists. It combines **archival contact sheet generation** and **standardized batch roll organizing & renaming** into an interface with a Python backend and clean HTML/CSS/JS frontend.

---

## Key Features

### 1. Archival Contact Sheet Generator (Tab 1)
- **Master Canvas Dimensions**: Default **11,500 × 9,200 px** archival master resolution (~105 MP print-ready with Lanczos resampling) and presets (8000×6400, 5750×4600, 4000×3200, Custom).
- **Smart Auto-Grid Engine**:
  - $\le 36$ photos: Classic 6 columns × 6 rows (36-exposure roll).
  - $\ge 37$ photos: Automatically selects 8 columns × 5 rows or 5 columns × 8 rows to maximize frame area.
- **Interactive Live Preview Viewport**:
  - Smooth **mouse-wheel zoom** centered around the cursor position.
  - **Click & drag panning** across the canvas.
  - **Double-click** instant fit reset.
  - Multi-sheet pagination (`◀ Prev` / `Next ▶`).
- **Vector Rebate Frame Numbering**:
  - Crisp filled vector arrows (`▶ 01A`, `▶ 02A`) rendered natively without font tofu box glitches.
  - Numbering modes: `rebate`, `simple` (`#01`), and `none`.
- **Authentic Film Aesthetics**:
  - Automatic 90° rotation for vertical frames simulating horizontal 35mm film strips.
  - Classic Darkroom Black and Clean Modern White themes.
- **Photo Queue Management**: Reorder (Move Up/Down), Sort A-Z, Reverse, Remove, or Add individual files.

---

### 2. Photo Organizer (Tab 2)
- **Standardized Archival Naming**:
  - Formats files into structured names: `YYYY-MM-DD_Film-Stock_01.ext` (with 2-digit zero-padded index: `01`, `02`, ..., `36`).
  - Standardizes the parent directory name into a unified archival format: `isopatrusute_YYYY-MM-DD_Film Stock`.
- **Smart Folder Parsing & Auto-Detection**:
  - Automatically extracts date (`YYYY-MM-DD`) and film stock from existing folder names (supports `isopatrusute_YYYY-MM-DD_Film-Stock`, `isopatrusute_order-XXXXX_YYYY-MM-DD_Film-Stock`, etc.).
- **Real-Time Dual-Column Preview Table**:
  - Side-by-side comparison: **Original Filename** ➔ **New Archival Name**.
  - Instant reactive updates (<10ms) whenever Date or Film Stock inputs change.
- **Reverse Renaming Order Toggle**:
  - One-click `N → 1` reverse sequence to fix rolls scanned backwards by labs.
- **Interactive Frame Thumbnail**:
  - Click any row to view high-resolution thumbnail and metadata.
- **Dual Operation Modes**:
  - **Rename In-Place (Folder & Files)**: Safe two-pass rename preventing collisions.
  - **Safe Copy to New Folder**: Duplicates and standardizes files into target folder leaving raw scans untouched.

---

## Project Structure

```
filmPhotoOrganizer/
├── main.py              # Application entry point: starts server & opens browser
├── server.py            # RESTful API router and static file server
├── config.py            # Global presets, themes, extensions, default grid configs
├── utils.py             # Metadata parsing, cross-platform font loading, thumbnails
├── generator.py         # Archival contact sheet rendering engine
├── organizer.py         # Batch renaming, safe copy, and file tree management engine
├── requirements.txt     # Dependencies (Pillow)
├── README.md            # Documentation
└── static/
    ├── index.html       # Single-page interface with Contact Sheet & Organizer tabs
    ├── css/
    │   └── style.css    # Modern darkroom UI, responsive flex/grid layouts
    └── js/
        ├── app.js       # Main state coordinator, tabs, toasts, native reveal
        ├── contact.js   # Contact sheet interactive queue, pan/zoom, generation
        └── organizer.js # Organizer batch renaming table and thumbnail preview
```
