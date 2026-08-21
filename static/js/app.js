/**
 * Film Photo Organizer - Global App Coordinator
 */

let activeTab = 'organizer';
let lastActiveFolderPath = '';

// Toast Notification Manager
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const iconMap = {
    success: '<span style="color: var(--accent-emerald); font-weight: 700;">[OK]</span>',
    error: '<span style="color: var(--accent-rose); font-weight: 700;">[ERR]</span>',
    info: '<span style="color: var(--accent-cyan); font-weight: 700;">[i]</span>'
  };

  toast.innerHTML = `${iconMap[type] || ''}<div>${message}</div>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 260);
  }, duration);
}

// Tab Switcher
function switchMainTab(tabId) {
  activeTab = tabId;

  document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

  const activeNavBtn = document.getElementById(`tab-btn-${tabId}`);
  const activePane = document.getElementById(`tab-${tabId}`);

  if (activeNavBtn) activeNavBtn.classList.add('active');
  if (activePane) activePane.classList.add('active');

  // Trigger preview update or UI refresh if needed
  if (tabId === 'contact') {
    if (window.schedulePreviewUpdate) window.schedulePreviewUpdate(true);
  }
}

// Sub-Tab Switcher (Metadata vs Layout)
function switchSettingsSubTab(subTabId) {
  document.querySelectorAll('.sub-tab').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.sub-tab-content').forEach(c => c.classList.remove('active'));

  const btn = document.getElementById(`subtab-${subTabId}-btn`);
  const content = document.getElementById(`subtab-${subTabId}`);

  if (btn) btn.classList.add('active');
  if (content) content.classList.add('active');
}

// Reveal Active Folder in Native File Manager
async function revealActiveFolder(customPath) {
  const path = customPath || lastActiveFolderPath || 
               document.getElementById('contact-source-input').value.trim() || 
               document.getElementById('organizer-source-input').value.trim();

  if (!path) {
    showToast("No active folder path specified yet.", "info");
    return;
  }

  try {
    const res = await fetch('/api/system/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    });
    const data = await res.json();
    if (data.success) {
      showToast("Opened folder in file manager.", "success");
    } else {
      showToast(data.error || "Could not open folder.", "error");
    }
  } catch (err) {
    showToast("Failed to contact server.", "error");
  }
}

// Clear All Loaded Photos across Both Tabs
function clearLoadedPhotos() {
  if (window.resetOrganizerState) window.resetOrganizerState();
  if (window.resetContactState) window.resetContactState();
  lastActiveFolderPath = '';
  showToast("Cleared all loaded photos from both tabs.", "info");
}

// Confirmation Modal Manager
let confirmedCallback = null;

function showConfirmModal(title, bodyHtml, onConfirm) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  confirmedCallback = onConfirm;
  document.getElementById('confirm-modal').style.display = 'flex';
}

function closeConfirmModal() {
  document.getElementById('confirm-modal').style.display = 'none';
  confirmedCallback = null;
}

function executeConfirmedAction() {
  if (confirmedCallback) {
    const fn = confirmedCallback;
    closeConfirmModal();
    fn();
  }
}

// Real-Time Chunked NDJSON Stream Consumer
async function consumeNdjsonStream(response, onMessage) {
  if (!response.body) {
    const data = await response.json();
    onMessage(data);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Retain incomplete chunk

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const parsed = JSON.parse(line);
        onMessage(parsed);
      } catch (e) {
        console.warn("NDJSON parse error:", e, line);
      }
    }
  }

  if (buffer && buffer.trim()) {
    try {
      const parsed = JSON.parse(buffer);
      onMessage(parsed);
    } catch (e) {}
  }
}

// Drag & Drop Universal Processor
async function processDataTransferItems(dataTransfer) {
  // 1. Try text / uri-list path resolution first
  try {
    const textDrop = (dataTransfer.getData('text/plain') || dataTransfer.getData('text/uri-list') || '').trim();
    if (textDrop) {
      const res = await fetch('/api/resolve-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: textDrop })
      });
      const data = await res.json();
      if (data.valid && data.path) {
        return { folderPath: data.path, count: 0, isLocalPath: true };
      }
    }
  } catch (e) {
    console.warn('Text drop path check failed:', e);
  }

  // 2. Extract files using directory entry traversal or standard files
  const items = dataTransfer.items;
  const filesList = [];
  let detectedFolderName = '';

  if (items && items.length > 0) {
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null;
        if (entry) {
          if (entry.isDirectory && !detectedFolderName) {
            detectedFolderName = entry.name;
          }
          await traverseFileEntry(entry, '', filesList);
        } else {
          const file = item.getAsFile();
          if (file) filesList.push({ file, path: file.name });
        }
      }
    }
  } else if (dataTransfer.files && dataTransfer.files.length > 0) {
    for (let i = 0; i < dataTransfer.files.length; i++) {
      const file = dataTransfer.files[i];
      filesList.push({ file, path: file.name });
    }
  }

  if (filesList.length === 0) {
    return null;
  }

  // Check if native file.path is available (e.g. Electron / desktop webview)
  if (filesList[0].file && filesList[0].file.path) {
    const p = filesList[0].file.path;
    const parentDir = p.replace(/[/\\][^/\\]+$/, '');
    if (parentDir) {
      return { folderPath: parentDir, count: filesList.length, isLocalPath: true };
    }
  }

  // Auto-locate the real original folder on local disk (e.g. in Downloads, Pictures, Desktop)
  if (detectedFolderName) {
    try {
      const sampleNames = filesList.slice(0, 10).map(f => f.file.name);
      const res = await fetch('/api/locate-dropped-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folder_name: detectedFolderName,
          filenames: sampleNames
        })
      });
      const data = await res.json();
      if (data && data.found && data.path) {
        return {
          folderPath: data.path,
          count: filesList.length,
          isLocalPath: true
        };
      }
    } catch (e) {
      console.warn("Folder auto-locate error:", e);
    }
  }

  // Fallback: upload dropped files to staging directory
  showToast(`Staging ${filesList.length} dropped photo(s)...`, 'info', 2000);
  const uploadRes = await uploadDroppedFilesBatch(filesList, detectedFolderName || 'dropped_roll');
  if (uploadRes && uploadRes.success && uploadRes.folder_path) {
    return {
      folderPath: uploadRes.folder_path,
      count: uploadRes.count,
      files: uploadRes.files,
      isLocalPath: false
    };
  }

  return null;
}

async function traverseFileEntry(entry, currentPath, result) {
  const validExtensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif', '.webp', '.dng'];
  if (entry.isFile) {
    const file = await new Promise((resolve) => entry.file(resolve));
    if (validExtensions.some(ext => file.name.toLowerCase().endsWith(ext))) {
      result.push({ file, path: currentPath ? `${currentPath}/${file.name}` : file.name });
    }
  } else if (entry.isDirectory) {
    const dirReader = entry.createReader();
    const entries = await readAllDirectoryEntries(dirReader);
    for (const child of entries) {
      await traverseFileEntry(child, currentPath ? `${currentPath}/${entry.name}` : entry.name, result);
    }
  }
}

function readAllDirectoryEntries(dirReader) {
  return new Promise((resolve) => {
    const allEntries = [];
    const read = () => {
      dirReader.readEntries((entries) => {
        if (!entries || entries.length === 0) {
          resolve(allEntries);
        } else {
          allEntries.push(...entries);
          read();
        }
      }, () => resolve(allEntries));
    };
    read();
  });
}

async function uploadDroppedFilesBatch(filesList, folderName) {
  const payloadFiles = [];
  for (const item of filesList) {
    const b64 = await readFileAsBase64String(item.file);
    payloadFiles.push({
      name: item.file.name,
      data: b64
    });
  }

  const res = await fetch('/api/upload-dropped', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      folder_name: folderName || 'dropped_roll',
      files: payloadFiles
    })
  });
  return await res.json();
}

function readFileAsBase64String(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// URL Params & Initialization
document.addEventListener('DOMContentLoaded', () => {
  document.documentElement.setAttribute('data-theme', 'dark');
  localStorage.removeItem('fpo_theme');

  // Check URL query parameters for auto-load
  const urlParams = new URLSearchParams(window.location.search);
  const initialPath = urlParams.get('path');
  if (initialPath) {
    if (window.loadContactFolder) window.loadContactFolder(initialPath);
    if (window.loadOrganizerFolder) window.loadOrganizerFolder(initialPath);
  }
});

