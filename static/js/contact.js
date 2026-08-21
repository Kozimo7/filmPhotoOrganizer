/**
 * Contact Sheet Generator - Frontend Logic & Interactive Live Preview
 */

let contactPhotos = [];
let contactSelectedIndices = new Set();
let previewPageIndex = 0;
let totalPreviewPages = 1;
let previewDebounceTimer = null;
let isContactGenerating = false;

// Zoom & Pan State
let zoomScale = 1.0;
let panX = 0;
let panY = 0;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;

// Browse Source Folder
async function browseContactSource() {
  try {
    const res = await fetch('/api/browse/folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: "Select Source Folder with Photos" })
    });
    const data = await res.json();
    if (data.path) {
      document.getElementById('contact-source-input').value = data.path;
      lastActiveFolderPath = data.path;
      loadContactFolder(data.path);
    }
  } catch (err) {
    showToast("Error opening folder picker.", "error");
  }
}

// Browse Output Folder
async function browseContactOutput() {
  try {
    const res = await fetch('/api/browse/folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: "Select Output Folder for Contact Sheet" })
    });
    const data = await res.json();
    if (data.path) {
      document.getElementById('contact-output-input').value = data.path;
    }
  } catch (err) {
    showToast("Error opening folder picker.", "error");
  }
}

// Add Individual Files
async function addIndividualContactFiles() {
  try {
    const res = await fetch('/api/browse/files', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: "Select Photos to Add" })
    });
    const data = await res.json();
    if (data.files && data.files.length > 0) {
      const existingPaths = new Set(contactPhotos.map(p => p.path));
      const newFiles = data.files.filter(f => !existingPaths.has(f));
      if (newFiles.length > 0) {
        scanContactFilesList([...contactPhotos.map(p => p.path), ...newFiles]);
      }
    }
  } catch (err) {
    showToast("Error selecting files.", "error");
  }
}

// Load Folder
async function loadContactFolder(folderPath) {
  if (!folderPath) return;

  try {
    const res = await fetch('/api/contact/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        folder_path: folderPath,
        canvas_width: getSelectedCanvasWidth(),
        canvas_height: getSelectedCanvasHeight()
      })
    });
    const data = await res.json();

    if (data.error) {
      showToast(`Error: ${data.error}`, "error");
      return;
    }

    contactPhotos = data.photos || [];
    if (data.roll_title) document.getElementById('contact-meta-title').value = data.roll_title;
    if (data.date_str) document.getElementById('contact-meta-date').value = data.date_str;
    if (data.film_stock) document.getElementById('contact-meta-film').value = data.film_stock;

    if (data.auto_cols && data.auto_rows) {
      document.getElementById('contact-columns-input').value = data.auto_cols;
      document.getElementById('contact-rows-input').value = data.auto_rows;
    }

    if (!document.getElementById('contact-output-input').value.trim()) {
      document.getElementById('contact-output-input').value = folderPath;
    }

    previewPageIndex = 0;
    renderContactQueueTable();
    updateContactUI();
    schedulePreviewUpdate(true);
    showToast(`Loaded ${contactPhotos.length} photos.`, "success");
  } catch (err) {
    showToast("Failed to scan folder.", "error");
  }
}

// Scan List of Files Directly
async function scanContactFilesList(filePaths) {
  try {
    const res = await fetch('/api/contact/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        files: filePaths,
        canvas_width: getSelectedCanvasWidth(),
        canvas_height: getSelectedCanvasHeight()
      })
    });
    const data = await res.json();
    contactPhotos = data.photos || [];

    if (data.auto_cols && data.auto_rows) {
      document.getElementById('contact-columns-input').value = data.auto_cols;
      document.getElementById('contact-rows-input').value = data.auto_rows;
    }

    renderContactQueueTable();
    updateContactUI();
    schedulePreviewUpdate(true);
  } catch (err) {
    showToast("Error loading files.", "error");
  }
}

// Render Queue Table
function renderContactQueueTable() {
  const tbody = document.getElementById('contact-queue-tbody');
  tbody.innerHTML = '';

  if (contactPhotos.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="5">No photos loaded. Select a folder or drop images above.</td>
      </tr>`;
    return;
  }

  contactPhotos.forEach((photo, idx) => {
    const tr = document.createElement('tr');
    tr.dataset.index = idx;
    if (contactSelectedIndices.has(idx)) {
      tr.classList.add('selected');
    }

    const isPort = photo.orientation === 'Port';
    tr.innerHTML = `
      <td style="text-align: center; color: var(--text-subtle);">${idx + 1}</td>
      <td title="${photo.path}"><strong>${escapeHtml(photo.filename)}</strong></td>
      <td style="text-align: center; font-family: var(--font-mono); font-size: 0.76rem;">${photo.width}×${photo.height}</td>
      <td style="text-align: center;">
        <span class="badge-orient ${isPort ? 'port' : 'land'}">${photo.orientation}</span>
      </td>
      <td style="text-align: center;">
        <button class="btn-remove-row" title="Remove" onclick="event.stopPropagation(); removeQueueIndex(${idx})">✕</button>
      </td>
    `;

    tr.addEventListener('click', (e) => {
      if (e.shiftKey) {
        // Multi select range
        contactSelectedIndices.add(idx);
      } else if (e.metaKey || e.ctrlKey) {
        if (contactSelectedIndices.has(idx)) contactSelectedIndices.delete(idx);
        else contactSelectedIndices.add(idx);
      } else {
        contactSelectedIndices.clear();
        contactSelectedIndices.add(idx);
      }
      renderContactQueueTable();
    });

    tbody.appendChild(tr);
  });
}

function updateContactUI() {
  const count = contactPhotos.length;
  document.getElementById('contact-badge').textContent = count;
  document.getElementById('queue-count-tag').textContent = `${count} photo${count !== 1 ? 's' : ''}`;

  const cols = parseInt(document.getElementById('contact-columns-input').value) || 6;
  const rows = parseInt(document.getElementById('contact-rows-input').value) || 6;
  const perSheet = cols * rows;
  totalPreviewPages = Math.max(1, Math.ceil(count / perSheet));

  document.getElementById('generate-contact-btn').disabled = count === 0 || isContactGenerating;
  document.getElementById('contact-status-text').textContent = 
    count > 0 ? `Loaded ${count} photos • ${totalPreviewPages} sheet${totalPreviewPages > 1 ? 's' : ''} (${cols}×${rows} grid)` : 'Ready. Select a folder to begin.';
}

// Queue Actions
function moveQueueItem(direction) {
  if (contactSelectedIndices.size === 0) return;
  const indices = Array.from(contactSelectedIndices).sort((a, b) => direction < 0 ? a - b : b - a);

  for (const idx of indices) {
    const targetIdx = idx + direction;
    if (targetIdx >= 0 && targetIdx < contactPhotos.length) {
      const temp = contactPhotos[idx];
      contactPhotos[idx] = contactPhotos[targetIdx];
      contactPhotos[targetIdx] = temp;
    }
  }

  // Shift selected indices
  const newSelected = new Set();
  indices.forEach(idx => {
    const targetIdx = idx + direction;
    if (targetIdx >= 0 && targetIdx < contactPhotos.length) {
      newSelected.add(targetIdx);
    } else {
      newSelected.add(idx);
    }
  });
  contactSelectedIndices = newSelected;

  renderContactQueueTable();
  schedulePreviewUpdate();
}

function sortQueueAZ() {
  contactPhotos.sort((a, b) => a.filename.localeCompare(b.filename, undefined, { numeric: true, sensitivity: 'base' }));
  contactSelectedIndices.clear();
  renderContactQueueTable();
  schedulePreviewUpdate();
}

function reverseQueue() {
  contactPhotos.reverse();
  contactSelectedIndices.clear();
  renderContactQueueTable();
  schedulePreviewUpdate();
}

function removeSelectedQueueItems() {
  if (contactSelectedIndices.size === 0) return;
  contactPhotos = contactPhotos.filter((_, idx) => !contactSelectedIndices.has(idx));
  contactSelectedIndices.clear();
  renderContactQueueTable();
  updateContactUI();
  schedulePreviewUpdate();
}

function removeQueueIndex(idx) {
  contactPhotos.splice(idx, 1);
  contactSelectedIndices.delete(idx);
  renderContactQueueTable();
  updateContactUI();
  schedulePreviewUpdate();
}

// Config Helpers
function getSelectedCanvasWidth() {
  const preset = document.getElementById('contact-preset-select').value;
  if (preset === 'Custom Dimensions') {
    return parseInt(document.getElementById('contact-custom-w').value) || 11500;
  }
  const dims = {
    "11500 x 9200 (Archival Master - Default)": 11500,
    "8000 x 6400 (Standard Large Print)": 8000,
    "5750 x 4600 (Medium Print)": 5750,
    "4000 x 3200 (Screen / Web Preview)": 4000
  };
  return dims[preset] || 11500;
}

function getSelectedCanvasHeight() {
  const preset = document.getElementById('contact-preset-select').value;
  if (preset === 'Custom Dimensions') {
    return parseInt(document.getElementById('contact-custom-h').value) || 9200;
  }
  const dims = {
    "11500 x 9200 (Archival Master - Default)": 9200,
    "8000 x 6400 (Standard Large Print)": 6400,
    "5750 x 4600 (Medium Print)": 4600,
    "4000 x 3200 (Screen / Web Preview)": 3200
  };
  return dims[preset] || 9200;
}

function onPresetChanged() {
  const preset = document.getElementById('contact-preset-select').value;
  const isCustom = preset === 'Custom Dimensions';
  document.getElementById('custom-w-group').style.display = isCustom ? 'flex' : 'none';
  document.getElementById('custom-h-group').style.display = isCustom ? 'flex' : 'none';
  schedulePreviewUpdate();
}

function getContactConfigPayload() {
  return {
    canvas_width: getSelectedCanvasWidth(),
    canvas_height: getSelectedCanvasHeight(),
    columns: parseInt(document.getElementById('contact-columns-input').value) || 6,
    rows_per_sheet: parseInt(document.getElementById('contact-rows-input').value) || 6,
    theme: document.getElementById('contact-theme-select').value,
    numbering_style: document.getElementById('contact-numbering-select').value,
    rotate_portrait: document.getElementById('contact-opt-rotate').checked,
    show_header: document.getElementById('contact-opt-header').checked,
    show_captions: document.getElementById('contact-opt-captions').checked,
    show_frame_border: document.getElementById('contact-opt-border').checked,
    roll_title: document.getElementById('contact-meta-title').value,
    date_str: document.getElementById('contact-meta-date').value,
    film_stock: document.getElementById('contact-meta-film').value,
    camera_info: document.getElementById('contact-meta-camera').value,
    notes: document.getElementById('contact-meta-notes').value
  };
}

// Live Preview Updater
function schedulePreviewUpdate(immediate = false) {
  if (previewDebounceTimer) clearTimeout(previewDebounceTimer);

  if (immediate) {
    requestPreviewUpdate();
  } else {
    previewDebounceTimer = setTimeout(requestPreviewUpdate, 120);
  }
}

async function requestPreviewUpdate(force = false) {
  if (contactPhotos.length === 0) {
    document.getElementById('preview-canvas-img').style.display = 'none';
    document.getElementById('preview-placeholder').style.display = 'block';
    updatePaginationState();
    return;
  }

  const badge = document.getElementById('preview-status-badge');
  badge.textContent = "Updating...";
  badge.style.color = "var(--accent-amber)";

  const config = getContactConfigPayload();
  const photoPaths = contactPhotos.map(p => p.path);

  try {
    const res = await fetch('/api/contact/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        config,
        photos: photoPaths,
        page_index: previewPageIndex,
        preview_scale: 0.12
      })
    });
    const data = await res.json();

    if (data.image) {
      const img = document.getElementById('preview-canvas-img');
      img.src = data.image;
      img.style.display = 'block';
      document.getElementById('preview-placeholder').style.display = 'none';

      totalPreviewPages = data.total_pages || 1;
      previewPageIndex = data.page_index || 0;
      updatePaginationState();

      badge.textContent = "Live Preview";
      badge.style.color = "var(--accent-emerald)";
    }
  } catch (err) {
    badge.textContent = "Preview Error";
    badge.style.color = "var(--accent-rose)";
  }
}

function updatePaginationState() {
  document.getElementById('preview-page-indicator').textContent = 
    contactPhotos.length > 0 ? `Sheet ${previewPageIndex + 1} of ${totalPreviewPages}` : 'Sheet 1 of 1';
  document.getElementById('preview-prev-btn').disabled = previewPageIndex <= 0;
  document.getElementById('preview-next-btn').disabled = previewPageIndex >= totalPreviewPages - 1;
}

function changePreviewPage(delta) {
  const newPage = previewPageIndex + delta;
  if (newPage >= 0 && newPage < totalPreviewPages) {
    previewPageIndex = newPage;
    requestPreviewUpdate(true);
  }
}

// Interactive Zoom & Pan
let panRafId = null;

function applyTransform() {
  const stage = document.getElementById('preview-stage');
  if (!stage) return;
  stage.style.transform = `translate3d(${panX}px, ${panY}px, 0) scale(${zoomScale})`;
  const zoomText = document.getElementById('zoom-level-text');
  if (zoomText) {
    zoomText.textContent = `${Math.round(zoomScale * 100)}%`;
  }
}

function zoomPreview(delta) {
  zoomScale = Math.max(0.2, Math.min(5.0, zoomScale + delta));
  applyTransform();
}

function resetPreviewZoom() {
  zoomScale = 1.0;
  panX = 0;
  panY = 0;
  applyTransform();
}

function setupZoomAndPan() {
  const viewport = document.getElementById('preview-viewport');
  if (!viewport) return;

  // Prevent default ghost image dragging on both viewport and img
  viewport.addEventListener('dragstart', (e) => e.preventDefault());
  const canvasImg = document.getElementById('preview-canvas-img');
  if (canvasImg) {
    canvasImg.addEventListener('dragstart', (e) => e.preventDefault());
  }

  // Smooth mouse wheel zoom centered around cursor position
  viewport.addEventListener('wheel', (e) => {
    e.preventDefault();
    const rect = viewport.getBoundingClientRect();
    const mouseX = e.clientX - rect.left - (rect.width / 2);
    const mouseY = e.clientY - rect.top - (rect.height / 2);

    const zoomFactor = e.deltaY < 0 ? 1.15 : (1 / 1.15);
    const prevScale = zoomScale;
    zoomScale = Math.max(0.2, Math.min(5.0, zoomScale * zoomFactor));

    // Shift pan offset so point under cursor stays invariant
    panX = mouseX - (mouseX - panX) * (zoomScale / prevScale);
    panY = mouseY - (mouseY - panY) * (zoomScale / prevScale);

    applyTransform();
  }, { passive: false });

  // Click & Drag pan
  viewport.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    isPanning = true;
    startPanX = e.clientX - panX;
    startPanY = e.clientY - panY;
    viewport.classList.add('dragging');
  });

  window.addEventListener('mousemove', (e) => {
    if (!isPanning) return;
    e.preventDefault();
    panX = e.clientX - startPanX;
    panY = e.clientY - startPanY;

    if (!panRafId) {
      panRafId = requestAnimationFrame(() => {
        applyTransform();
        panRafId = null;
      });
    }
  });

  window.addEventListener('mouseup', () => {
    if (isPanning) {
      isPanning = false;
      viewport.classList.remove('dragging');
      if (panRafId) {
        cancelAnimationFrame(panRafId);
        panRafId = null;
      }
      applyTransform();
    }
  });

  // Double click reset
  viewport.addEventListener('dblclick', resetPreviewZoom);
}

// Generate Full Master Contact Sheet
async function generateFullContactSheet() {
  if (contactPhotos.length === 0 || isContactGenerating) return;

  const outputDir = document.getElementById('contact-output-input').value.trim() || 
                    document.getElementById('contact-source-input').value.trim();

  if (!outputDir) {
    showToast("Please select an output folder.", "error");
    return;
  }

  isContactGenerating = true;
  document.getElementById('generate-contact-btn').disabled = true;
  document.getElementById('contact-progress-container').style.display = 'block';
  document.getElementById('contact-progress-bar').style.width = '0%';
  document.getElementById('contact-status-text').textContent = 'Starting master archival contact sheet generator...';

  const jobId = 'contact_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
  let isPolling = true;

  const pollInterval = setInterval(async () => {
    if (!isPolling) return;
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      if (!res.ok) return;
      const job = await res.json();
      if (job && job.status === 'running') {
        const pct = Math.max(0, Math.min(100, job.percent || 0));
        document.getElementById('contact-progress-bar').style.width = `${pct}%`;
        if (job.message) {
          document.getElementById('contact-status-text').textContent = job.message;
        }
      }
    } catch (e) {}
  }, 75);

  try {
    const config = getContactConfigPayload();
    const res = await fetch('/api/contact/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        config,
        photos: contactPhotos.map(p => p.path),
        output_dir: outputDir,
        format: "JPEG",
        quality: 95,
        job_id: jobId
      })
    });
    const data = await res.json();

    isPolling = false;
    clearInterval(pollInterval);

    if (data.success) {
      document.getElementById('contact-progress-bar').style.width = '100%';
      document.getElementById('contact-status-text').textContent = `Generated ${data.count} master sheet(s) successfully in ${data.output_dir}`;
      showToast(`Master contact sheet(s) generated!`, "success", 5000);
      showConfirmModal(
        "Contact Sheet Generated",
        `<p style="margin-bottom: 8px;">Successfully generated <strong>${data.count}</strong> master contact sheet(s) in:</p>
         <div class="modal-path-box">
           <code>${escapeHtml(data.output_dir)}</code>
         </div>`,
        () => revealActiveFolder(data.output_dir)
      );
      document.getElementById('modal-confirm-btn').textContent = "Open in Folder";
    } else {
      document.getElementById('contact-status-text').textContent = `Generation error: ${data.error}`;
      showToast(`Error: ${data.error}`, "error");
    }
  } catch (err) {
    isPolling = false;
    clearInterval(pollInterval);
    document.getElementById('contact-status-text').textContent = 'Failed to generate contact sheet.';
    showToast("Failed to connect to server.", "error");
  } finally {
    isPolling = false;
    clearInterval(pollInterval);
    isContactGenerating = false;
    document.getElementById('generate-contact-btn').disabled = false;
    setTimeout(() => {
      document.getElementById('contact-progress-container').style.display = 'none';
      document.getElementById('contact-progress-bar').style.width = '0%';
    }, 3000);
  }
}

// Drag & Drop Setup
function setupContactDropzone() {
  const dropzone = document.getElementById('contact-dropzone');
  if (!dropzone) return;

  ['dragenter', 'dragover'].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', async (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('dragover');

    try {
      const result = await processDataTransferItems(e.dataTransfer);
      if (result && result.folderPath) {
        document.getElementById('contact-source-input').value = result.folderPath;
        lastActiveFolderPath = result.folderPath;
        loadContactFolder(result.folderPath);
        showToast(`Loaded ${result.count ? result.count + ' ' : ''}photos into Contact Sheet Generator!`, 'success');
      } else {
        showToast("No supported photos found in dropped item.", "info");
      }
    } catch (err) {
      showToast("Failed to process dropped files: " + err.message, "error");
    }
  });
}

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// Reset / Clear Contact Sheet Generator State
function resetContactState() {
  contactPhotos = [];
  contactSelectedIndices.clear();
  previewPageIndex = 0;
  totalPreviewPages = 1;

  document.getElementById('contact-source-input').value = '';
  document.getElementById('contact-output-input').value = '';
  document.getElementById('contact-meta-title').value = 'ANALOG ROLL #01';
  document.getElementById('contact-meta-date').value = '';
  document.getElementById('contact-meta-film').value = '';
  document.getElementById('contact-meta-camera').value = '';
  document.getElementById('contact-meta-notes').value = '';

  const previewImg = document.getElementById('preview-canvas-img');
  const previewPlaceholder = document.getElementById('preview-placeholder');
  if (previewImg) {
    previewImg.src = '';
    previewImg.style.display = 'none';
  }
  if (previewPlaceholder) {
    previewPlaceholder.style.display = 'block';
  }

  renderContactQueueTable();
  updateContactUI();
  updatePaginationState();
  resetPreviewZoom();
  document.getElementById('contact-status-text').textContent = 'Ready. Select or drop a folder to begin.';
}

window.resetContactState = resetContactState;

document.addEventListener('DOMContentLoaded', () => {
  setupZoomAndPan();
  setupContactDropzone();
});
