/**
 * Photo Organizer - Frontend Logic & Interactive Batch Renaming Table
 */

let organizerMatchedFiles = [];
let organizerFilePairs = [];
let organizerSourcePath = '';
let organizerSelectedFile = '';
let organizerOperationMode = 'inplace';
let isOrganizerProcessing = false;
let organizerDebounceTimer = null;

// Browse Source
async function browseOrganizerSource() {
  try {
    const res = await fetch('/api/browse/folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: "Select Source Folder with Film Scans" })
    });
    const data = await res.json();
    if (data.path) {
      document.getElementById('organizer-source-input').value = data.path;
      lastActiveFolderPath = data.path;
      loadOrganizerFolder(data.path);
    }
  } catch (err) {
    showToast("Error opening folder picker.", "error");
  }
}

// Browse Output
async function browseOrganizerOutput() {
  try {
    const res = await fetch('/api/browse/folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: "Select Destination Directory for Safe Copy" })
    });
    const data = await res.json();
    if (data.path) {
      document.getElementById('organizer-output-input').value = data.path;
    }
  } catch (err) {
    showToast("Error opening folder picker.", "error");
  }
}

// Load & Analyze Folder
async function loadOrganizerFolder(folderPath) {
  if (!folderPath) return;

  try {
    const res = await fetch('/api/organizer/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder_path: folderPath })
    });
    const data = await res.json();

    if (data.error) {
      showToast(`Error: ${data.error}`, "error");
      return;
    }

    organizerSourcePath = data.folder_path;
    organizerMatchedFiles = data.files || [];
    organizerFilePairs = data.pairs || [];

    document.getElementById('organizer-date-input').value = data.date_str || '';
    document.getElementById('organizer-film-input').value = data.film_stock || '';

    renderOrganizerTable();
    updateOrganizerUI();
    updateFolderPreviewText();

    if (organizerMatchedFiles.length > 0) {
      selectOrganizerRow(organizerMatchedFiles[0]);
    }

    showToast(`Detected ${organizerMatchedFiles.length} photos in roll.`, "success");
  } catch (err) {
    showToast("Failed to analyze folder.", "error");
  }
}

// Reactively Recalculate New Names
function onOrganizerMetaChanged() {
  if (organizerDebounceTimer) clearTimeout(organizerDebounceTimer);
  organizerDebounceTimer = setTimeout(recomputeOrganizerNames, 50);
}

async function recomputeOrganizerNames() {
  const dateStr = document.getElementById('organizer-date-input').value.trim();
  const filmStock = document.getElementById('organizer-film-input').value.trim();
  const reverseOrder = document.getElementById('organizer-reverse-chk').checked;

  updateFolderPreviewText();

  if (organizerMatchedFiles.length === 0) return;

  try {
    const res = await fetch('/api/organizer/preview-names', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        files: organizerMatchedFiles,
        date_str: dateStr,
        film_stock: filmStock,
        reverse_order: reverseOrder
      })
    });
    const data = await res.json();

    organizerFilePairs = data.pairs || [];
    renderOrganizerTable();
    updateOrganizerUI();

    // Update selected info if active
    if (organizerSelectedFile) {
      const pair = organizerFilePairs.find(p => p.original === organizerSelectedFile);
      if (pair) {
        document.getElementById('info-new-name').textContent = pair.new_name;
      }
    }
  } catch (err) {
    console.error("Error updating preview names:", err);
  }
}

function updateFolderPreviewText() {
  const date = document.getElementById('organizer-date-input').value.trim() || 'YYYY-MM-DD';
  const film = document.getElementById('organizer-film-input').value.trim() || 'Film-Stock';
  const preview = `isopatrusute_${date}_${film}`;
  const el = document.getElementById('folder-preview-inplace');
  if (el) el.textContent = preview;
}

// Operation Mode Switcher
function onOperationModeChanged(mode) {
  organizerOperationMode = mode;

  document.getElementById('mode-card-inplace').classList.toggle('active', mode === 'inplace');
  document.getElementById('mode-card-copy').classList.toggle('active', mode === 'copy');

  const outputGroup = document.getElementById('organizer-output-group');
  const btn = document.getElementById('process-organizer-btn');

  if (mode === 'inplace') {
    outputGroup.style.opacity = '0.4';
    outputGroup.style.pointerEvents = 'none';
    btn.textContent = 'Rename Folder & Files';
  } else {
    outputGroup.style.opacity = '1';
    outputGroup.style.pointerEvents = 'auto';
    btn.textContent = 'Safe Copy Photos';
  }
}

// Render Table
function renderOrganizerTable() {
  const tbody = document.getElementById('organizer-tbody');
  tbody.innerHTML = '';

  window.organizerMatchedFiles = organizerMatchedFiles;
  window.organizerSelectedFile = organizerSelectedFile;
  window.selectOrganizerRow = selectOrganizerRow;

  if (organizerFilePairs.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="4">
          <div class="empty-guide-box">
            <div class="empty-guide-icon" aria-hidden="true">🎞️</div>
            <div class="empty-guide-title">No Film Scans Loaded</div>
            <p class="empty-guide-desc">Select or drop a folder containing raw photo scans to detect frames and preview standardized archival names.</p>
            <div class="empty-guide-formats">
              <span class="format-title">Auto-Detects Folder Patterns:</span>
              <div class="format-chips">
                <code>isopatrusute_YYYY-MM-DD_Film-Stock</code>
                <code>order-12345_YYYY-MM-DD_Film-Stock</code>
                <code>YYYY-MM-DD_Film-Stock</code>
              </div>
            </div>
          </div>
        </td>
      </tr>`;
    return;
  }

  organizerFilePairs.forEach((pair, idx) => {
    const tr = document.createElement('tr');
    tr.dataset.filename = pair.original;
    if (pair.original === organizerSelectedFile) {
      tr.classList.add('selected');
    }

    tr.innerHTML = `
      <td style="text-align: center; color: var(--text-subtle);">${idx + 1}</td>
      <td title="${pair.original}"><code>${escapeHtml(pair.original)}</code></td>
      <td style="text-align: center; color: var(--accent-amber);">➔</td>
      <td class="mono-target" title="${pair.new_name}"><strong>${escapeHtml(pair.new_name)}</strong></td>
    `;

    tr.addEventListener('click', () => {
      selectOrganizerRow(pair.original);
    });

    tbody.appendChild(tr);
  });
}

function selectOrganizerRow(filename) {
  organizerSelectedFile = filename;
  window.organizerSelectedFile = filename;

  document.querySelectorAll('#organizer-tbody tr').forEach(r => {
    r.classList.toggle('selected', r.dataset.filename === filename);
  });

  const fullPath = `${organizerSourcePath}/${filename}`;
  const thumbImg = document.getElementById('organizer-thumb-img');
  const placeholder = document.getElementById('organizer-thumb-placeholder');
  const infoBox = document.getElementById('organizer-selected-info');

  thumbImg.src = `/api/thumbnail?path=${encodeURIComponent(fullPath)}&size=300`;
  thumbImg.style.display = 'block';
  placeholder.style.display = 'none';
  infoBox.style.display = 'block';

  document.getElementById('info-original-name').textContent = filename;
  const pair = organizerFilePairs.find(p => p.original === filename);
  document.getElementById('info-new-name').textContent = pair ? pair.new_name : '';
}

function updateOrganizerUI() {
  const count = organizerMatchedFiles.length;
  document.getElementById('organizer-badge').textContent = count;
  document.getElementById('organizer-count-tag').textContent = `${count} photo${count !== 1 ? 's' : ''} detected`;

  const filmStock = document.getElementById('organizer-film-input').value.trim();
  const canProcess = count > 0 && filmStock.length > 0 && !isOrganizerProcessing;

  document.getElementById('process-organizer-btn').disabled = !canProcess;
  document.getElementById('organizer-status-text').textContent = 
    count > 0 ? `${count} photo${count !== 1 ? 's' : ''} ready to standardize.` : 'Select a folder to begin organizing.';
}

// Processing
function startOrganizerProcessing() {
  if (organizerMatchedFiles.length === 0 || isOrganizerProcessing) return;

  const dateStr = document.getElementById('organizer-date-input').value.trim();
  const filmStock = document.getElementById('organizer-film-input').value.trim();

  if (!dateStr || !filmStock) {
    showToast("Please make sure Date and Film Stock are filled.", "error");
    return;
  }

  const invalidChars = /[<>:"/\\|?*]/;
  if (invalidChars.test(filmStock)) {
    showToast("Film Stock contains invalid filesystem characters (< > : \" / \\ | ? *)", "error");
    return;
  }

  const targetFolderName = `isopatrusute_${dateStr}_${filmStock}`;

  if (organizerOperationMode === 'inplace') {
    showConfirmModal(
      "Confirm Rename In-Place",
      `<p>This will rename all <strong>${organizerMatchedFiles.length}</strong> photos inside the folder in-place and rename the folder to:</p>
       <p style="margin-top: 10px;"><code>${escapeHtml(targetFolderName)}</code></p>
       <p style="margin-top: 10px; color: var(--accent-amber);">Are you sure you want to proceed?</p>`,
      () => executeOrganizerBatch()
    );
  } else {
    executeOrganizerBatch();
  }
}

async function executeOrganizerBatch() {
  isOrganizerProcessing = true;
  document.getElementById('process-organizer-btn').disabled = true;
  document.getElementById('organizer-progress-container').style.display = 'block';
  document.getElementById('organizer-progress-bar').style.width = '0%';
  document.getElementById('organizer-status-text').textContent = 'Starting photo batch processing...';

  const dateStr = document.getElementById('organizer-date-input').value.trim();
  const filmStock = document.getElementById('organizer-film-input').value.trim();
  const reverseOrder = document.getElementById('organizer-reverse-chk').checked;
  const outputParent = document.getElementById('organizer-output-input').value.trim();

  const jobId = 'org_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
  let isPolling = true;

  const pollInterval = setInterval(async () => {
    if (!isPolling) return;
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      if (!res.ok) return;
      const job = await res.json();
      if (job && job.status === 'running') {
        const pct = Math.max(0, Math.min(100, job.percent || 0));
        document.getElementById('organizer-progress-bar').style.width = `${pct}%`;
        if (job.message) {
          document.getElementById('organizer-status-text').textContent = job.message;
        }
      }
    } catch (e) {}
  }, 75);

  try {
    const res = await fetch('/api/organizer/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode: organizerOperationMode,
        source_path: organizerSourcePath,
        output_parent: outputParent,
        date_str: dateStr,
        film_stock: filmStock,
        reverse_order: reverseOrder,
        files: organizerMatchedFiles,
        job_id: jobId
      })
    });
    const data = await res.json();

    isPolling = false;
    clearInterval(pollInterval);
    document.getElementById('organizer-progress-bar').style.width = '100%';

    if (data && !data.error) {
      const actionName = organizerOperationMode === 'inplace' ? 'Renamed' : 'Copied';
      showToast(`Successfully ${actionName.toLowerCase()} ${data.success_count} photos! Automatically loaded into Contact Sheet.`, "success", 5000);

      const newPath = data.final_folder_path || organizerSourcePath;
      lastActiveFolderPath = newPath;

      // Automatically load organized folder into Contact Sheet Generator
      if (window.loadContactFolder) {
        window.loadContactFolder(newPath);
      }

      // Clear Photo Organizer state after renaming
      resetOrganizerState();

      showConfirmModal(
        "Operation Completed",
        `<p style="margin-bottom: 8px;">Successfully ${actionName.toLowerCase()} <strong>${data.success_count}</strong> photo(s) into:</p>
         <div class="modal-path-box">
           <code>${escapeHtml(newPath)}</code>
         </div>
         <p style="margin-top: 10px; color: var(--accent-emerald); font-size: 0.88rem;">
           <strong>Folder automatically loaded into Contact Sheet Generator.</strong>
         </p>`,
        () => {
          switchMainTab('contact');
        }
      );
      document.getElementById('modal-confirm-btn').textContent = "Go to Contact Sheet";
    } else {
      const err = data?.error || "Processing failed";
      showToast(`Error: ${err}`, "error");
      document.getElementById('organizer-status-text').textContent = `Failed: ${err}`;
    }
  } catch (err) {
    isPolling = false;
    clearInterval(pollInterval);
    showToast("Processing failed: " + (err.message || err), "error");
  } finally {
    isPolling = false;
    clearInterval(pollInterval);
    isOrganizerProcessing = false;
    document.getElementById('process-organizer-btn').disabled = false;
    setTimeout(() => {
      document.getElementById('organizer-progress-container').style.display = 'none';
      document.getElementById('organizer-progress-bar').style.width = '0%';
    }, 2500);
  }
}

// Reset / Clear Organizer state after operation
function resetOrganizerState() {
  organizerMatchedFiles = [];
  organizerFilePairs = [];
  organizerSourcePath = '';
  organizerSelectedFile = '';

  document.getElementById('organizer-source-input').value = '';
  document.getElementById('organizer-output-input').value = '';
  document.getElementById('organizer-date-input').value = '';
  document.getElementById('organizer-film-input').value = '';
  document.getElementById('organizer-reverse-chk').checked = false;

  document.getElementById('organizer-badge').textContent = '0';
  document.getElementById('organizer-count-tag').textContent = '0 photos detected';
  document.getElementById('folder-preview-inplace').textContent = 'isopatrusute_...';

  // Clear thumbnail preview
  const thumbImg = document.getElementById('organizer-thumb-img');
  const thumbPlaceholder = document.getElementById('organizer-thumb-placeholder');
  const selectedInfo = document.getElementById('organizer-selected-info');
  if (thumbImg) { thumbImg.src = ''; thumbImg.style.display = 'none'; }
  if (thumbPlaceholder) thumbPlaceholder.style.display = 'flex';
  if (selectedInfo) selectedInfo.style.display = 'none';

  renderOrganizerTable();
  updateOrganizerUI();
  document.getElementById('organizer-status-text').textContent = 'Ready. Select or drop a folder to begin organizing.';
}

window.resetOrganizerState = resetOrganizerState;

// Drag & Drop Setup
function setupOrganizerDropzone() {
  const dropzone = document.getElementById('organizer-dropzone');
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
        document.getElementById('organizer-source-input').value = result.folderPath;
        lastActiveFolderPath = result.folderPath;
        loadOrganizerFolder(result.folderPath);
        showToast(`Loaded ${result.count ? result.count + ' ' : ''}photos into Organizer!`, 'success');
      } else {
        showToast("No supported photos found in dropped item.", "info");
      }
    } catch (err) {
      showToast("Failed to process dropped files: " + err.message, "error");
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  setupOrganizerDropzone();
});
