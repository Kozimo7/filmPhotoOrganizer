# Film Photo Organizer & Archival Contact Sheet Generator

A unified, modern web-based desktop application for analog film photographers and digital archivists. It combines **standardized batch roll organizing & renaming** and **ultra-high-resolution archival contact sheet generation** into a streamlined interface powered by a lightweight Python backend and a vanilla HTML/CSS/JavaScript frontend.

---

## Features Overview

### 1. Photo Organizer (Tab 1)
- **Standardized Archival Naming**:
  - Automatically renames photo scans into structured archival filenames: `YYYY-MM-DD_Film-Stock_01.ext` (with 2-digit zero-padded index: `01`, `02`, ..., `36`).
  - Standardizes the parent directory name into a unified catalog format: `isopatrusute_YYYY-MM-DD_Film Stock`.
- **Smart Folder Parsing & Auto-Detection**:
  - Automatically extracts roll date (`YYYY-MM-DD`) and film stock from folder names (supports formats like `isopatrusute_YYYY-MM-DD_Film-Stock`, `order-XXXXX_YYYY-MM-DD_Film-Stock`, etc.).
- **Real-Time Dual-Column Preview Table**:
  - Side-by-side comparison: **Original Filename** ➔ **New Standardized Archival Name**.
  - Instant reactive name previews (<10ms) whenever Date or Film Stock inputs change.
- **Reverse Renaming Order Toggle**:
  - One-click `N ➔ 1` reverse sequence option to correct rolls scanned backwards by flatbed scanners or labs.
- **Selected Frame Thumbnail Preview**:
  - Click any row in the renaming table to preview high-resolution frame details and target naming.
- **Dual Operation Modes**:
  - **Rename In-Place (Folder & Files)**: Two-pass atomic rename preventing collisions while updating both filenames and directory.
  - **Safe Copy to New Folder**: Duplicates and standardizes scans into a target directory, keeping original scans untouched.
- **Automatic Workflow Handoff**:
  - Once organized, the roll is automatically loaded into the **Contact Sheet Generator** for immediate proofing.

---

### 2. Archival Contact Sheet Generator (Tab 2)
- **Master Canvas Dimensions**:
  - Default **11,500 × 9,200 px** archival master resolution (~105 MP print-ready with Lanczos resampling).
  - Built-in presets: `8000 × 6400 (Large Print)`, `5750 × 4600 (Medium Print)`, `4000 × 3200 (Web Preview)`, and `Custom Dimensions`.
- **Smart Auto-Grid Engine**:
  - $\le 36$ photos: Classic 6 columns × 6 rows (standard 36-exposure roll).
  - $\ge 37$ photos: Automatically configures 8 columns × 5 rows or 5 columns × 8 rows to maximize frame area across multi-sheet sets.
- **Interactive Live Preview Viewport**:
  - Smooth **mouse-wheel zoom** centered around the cursor position.
  - **Click & drag panning** across high-resolution previews.
  - **Double-click** instant zoom-to-fit reset.
  - Multi-sheet pagination (`◀ Prev` / `Next ▶`).
- **Vector Rebate Frame Numbering**:
  - Crisp vector arrow markers (`▶ 01A`, `▶ 02A`) rendered natively.
  - Numbering styles: `Rebate Arrow (▶ 01A)`, `Simple (#01)`, and `None`.
- **Authentic Film Strip Aesthetics**:
  - Optional 90° rotation for vertical frames simulating horizontal 35mm film strips.
  - Customizable header banner, date, camera/lens metadata, and lab notes.
  - Visual themes: **Classic Darkroom Black** and **Clean Modern White**.
- **Photo Queue Management**:
  - Reorder photos (`▲ Move Up` / `▼ Move Down`), Sort Alphabetically (`A-Z`), Reverse Order (`⇄ Reverse`), or Remove individual items.

---

### 3. Core Architecture & Usability
- **Native Folder Auto-Locate Engine**:
  - When dragging and dropping a folder from the file system, the backend automatically locates and matches the local directory path on disk (searching `Downloads`, `Pictures`, `Desktop`, `Documents`, and local drives), eliminating staging overhead and operating directly in place.
- **Global Dual-Tab Clear Button**:
  - The header **Clear** button resets loaded queues, batch tables, metadata inputs, and live preview canvases across both application tabs simultaneously.
- **Asynchronous Background Processing & Verbose Progress**:
  - Long batch operations run in background worker threads with real-time status polling (`1/36`, `2/36` progress tracking).
- **Responsive Dark Mode Design**:
  - Fluid UI with adaptable flex/grid layouts fitting both small laptop viewports and ultra-wide desktop monitors.

---

## Project Structure

```
filmPhotoOrganizer/
├── main.py              # Application entry point: server binding & browser launcher
├── server.py            # RESTful API router, job state tracker & static file server
├── config.py            # Presets, color themes, supported extensions, grid settings
├── utils.py             # Metadata parsing, cross-platform font loading, thumbnails
├── generator.py         # Archival contact sheet rendering & compositing engine
├── organizer.py         # Batch renaming, safe copy & directory cataloging engine
├── requirements.txt     # Python package dependencies (Pillow)
├── test_server.py       # Integration test suite for all REST API endpoints
├── test_app.py          # Unit test suite for organizer and generator core logic
├── README.md            # Project documentation
└── static/
    ├── index.html       # Single-page interface (Photo Organizer & Contact Sheet tabs)
    ├── css/
    │   └── style.css    # Clean darkroom design system, fluid responsive layouts
    └── js/
        ├── app.js       # Global state coordinator, drag & drop, tab switching
        ├── contact.js   # Contact sheet interactive queue, pan/zoom, generation
        └── organizer.js # Organizer batch renaming table and thumbnail preview
```